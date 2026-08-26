from datetime import datetime, time, timedelta
from typing import List, Tuple, Union
import requests
from app.core.configurable_service.configurable_service import ServiceParamDescription
from app.core.time_series.data_sources.data_source import DataSource
from app.core.time_series.data_sources.mintaka.mintaka_query_builder import (
    MintakaQueryBuilder,
)
from aether_pylib.time_series.time_series import TimeSeries, TimeSeriesValue
from aether_pylib.time_series.time_scope import TimeScope, TimeScopeAdjustment
from aether_pylib.time_series.time_series_options import (
    TimeSeriesOptions,
    TimeSeriesOrdering,
)
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
from aether_pylib.time_series.time_series_response import TimeSeriesResponse
from app.core.config.logging import appLogging as logging
from app.core.time_series.data_sources.mintaka.ngsi_ld_entity_processing import (
    get_temporal_property_from_normalized_attribute,
    get_value_property_from_normalized_attribute,
)


import app.core.time_series.aggregations as aggregations


class MintakaDataSource(DataSource):
    """
    Mintaka data source implementation
    """

    def __init__(self, **kwargs):
        # initialize the data source
        self.service_url = kwargs["MINTAKA_SERVICE_URL"]
        self.tenant = kwargs["DEFAULT_TENANT"]
        self.context_url = kwargs["CONTEXT_URL"]
        self.default_entity_page_size = kwargs.get("DEFAULT_ENTITY_PAGE_SIZE", 50)

        # if any is None, raise exception
        if self.service_url is None or self.tenant is None or self.context_url is None:
            raise Exception(
                "Missing required parameters.\n" + str(self.params_description())
            )

    def params_description() -> ServiceParamDescription:
        """
        Description of the needed kwargs
        """
        return {
            "MINTAKA_SERVICE_URL": {
                "description": "URL of the temporal service",
                "type": str,
                "required": True,
                "default": "",
            },
            "DEFAULT_TENANT": {
                "description": "Tenant of the temporal service",
                "type": str,
                "required": True,
                "default": "",
            },
            "CONTEXT_URL": {
                "description": "URL of the context file",
                "type": str,
                "required": True,
                "default": "",
            },
            "DEFAULT_ENTITY_PAGE_SIZE": {
                "description": "Default page size for entity queries when paginating is possible",
                "type": int,
                "required": False,
                "default": 50,
            },
        }

    def health_check(self) -> bool:
        """
        Check if the data source is reachable (mintaka info endpoint)
        """
        response = requests.get(self.service_url + "/info")
        logging.info(
            "Mintaka health check: " + str(response.status_code) + " " + response.text
        )
        if response.status_code == 200:
            return True
        raise Exception(
            f"Mintaka health check failed: {response.status_code}\n" + response.text
        )

    def get_time_series(
        self,
        requests_list: List[TimeSeriesRequest],
    ) -> TimeSeriesResponse:
        """
        Process a list of time series requests. All mintaka requests are sent through the same
        session, so that the connection is reused.
        """
        results = []
        session = requests.Session()
        for request in requests_list:
            try:
                results.append(self.get_single_time_series_request(request, session))
            except Exception as e:
                logging.error("Error processing request: " + str(e))
        session.close()
        return results

    def get_single_time_series_request(
        self, request: TimeSeriesRequest, session: requests.Session
    ) -> TimeSeriesResponse:
        """
        Process a single time series request. The session is given as a parameter, so that it can be reused
        for multiple requests.
        """

        self.tenant = request.options.tenant

        time_series_response = TimeSeriesResponse(
            time_series=[],
            options=request.options,
        )

        has_where_clause = (
            request.options is not None and request.options.where is not None
        )

        if not has_where_clause:
            # query for each entity, ask mintaka and transform the response
            for entity_id in request.device_ids:
                new_series = self.__get_entity_data(
                    entity_id, request.measure_ids, request.options, session
                )
                time_series_response.time_series.extend(new_series)
        else:
            time_series_response.time_series = self.__get_entities_data_where_clause(
                request.device_ids, request.measure_ids, request.options, session
            )

        # apply period filtering if needed
        if request.options is not None and request.options.period is not None:
            new_time_series = []
            for series in time_series_response.time_series:
                new_time_series.append(
                    self.__period_list_series_filtering(series, request.options.period)
                )
            time_series_response.time_series = new_time_series

        # apply aggregation if needed
        if request.options is not None:
            if request.options.aggregation is not None:
                for time_series in time_series_response.time_series:
                    time_series.values = aggregations.aggregate(
                        request.options.aggregation, time_series.values
                    )

            if request.options.order == TimeSeriesOrdering.ASC:
                # order in ascending order (invert the list)
                for time_series in time_series_response.time_series:
                    time_series.values.reverse()

        return time_series_response

    def __get_entity_data(
        self,
        entity_id: str,
        attrs: List[str],
        options: TimeSeriesOptions,
        session: requests.Session,
    ):
        """
        Get the data of a single entity
        """
        query = self.__get_query_from_options(entity_id, attrs, options, session)

        response = session.send(query)

        if response.status_code not in [200, 206]:
            logging.error(
                "Error retrieving data from mintaka: "
                + str(response.status_code)
                + " "
                + response.text
            )
            return []

        response_json = response.json()

        if response_json is None:
            logging.error("None response received from Mintaka")
            return []

        time_series = self.__transform_ngsi_ld_response(response_json, attrs)

        # check if all needed data was returned,
        # if not, craft a new request until all data is returned
        remaining_data_options = [
            self.__get_remaining_data_options(time_serie, options)
            for time_serie in time_series
        ]

        logging.info("Remaining data options: " + str(remaining_data_options))

        next_request_options = self.__merge_options(remaining_data_options)

        logging.info("Next request options: " + str(next_request_options))

        if next_request_options is not None:
            # there is remaining data to be retrieved, send a new request
            # and append the result to the current time series

            next_time_series = self.__get_entity_data(
                entity_id, attrs, next_request_options, session
            )

            time_series = self.__merge_time_series(time_series, next_time_series)

        return time_series

    def __get_entities_data_where_clause(
        self,
        entity_ids: List[str],
        attrs: List[str],
        options: TimeSeriesOptions,
        session: requests.Session,
    ):

        next_page = None
        result = []
        while True:

            time_series, next_page = self.__get_entities_data_paginated(
                entity_ids, attrs, options, session, next_page
            )
            result.extend(time_series)

            if next_page is None:
                break

        return result

    def __get_entities_data_paginated(
        self,
        entity_ids: List[str],
        attrs: List[str],
        options: TimeSeriesOptions,
        session: requests.Session,
        page_anchor: str = None,
    ):
        """
        Get the data of a single entity
        """
        query = self.__get_query_from_options(page_anchor, attrs, options, session)

        response = session.send(query)

        if response.status_code not in [200, 206]:
            logging.error(
                "Error retrieving data from mintaka: "
                + str(response.status_code)
                + " "
                + response.text
            )
            return []

        response_json = response.json()

        if response_json is None:
            logging.error("None response received from Mintaka")
            return []

        # this returns multiple entities, so we need to process each one
        time_series = []

        for entity_data in response_json:
            time_series.extend(self.__transform_ngsi_ld_response(entity_data, attrs))

        # filter by the requested entities
        if entity_ids is not None and len(entity_ids) > 0:
            time_series = [
                serie for serie in time_series if serie.device_id in entity_ids
            ]

        next_page = response.headers.get("Next-Page")

        return time_series, next_page

    def __merge_time_series(self, seriesA: List[TimeSeries], seriesB: List[TimeSeries]):
        """
        Merge two lists of time series into a single one
        """
        values_dict = {
            (series.device_id, series.measure_id): series.values for series in seriesA
        }

        for series in seriesB:
            if (series.device_id, series.measure_id) in values_dict:
                values_dict[(series.device_id, series.measure_id)].extend(series.values)
            else:
                values_dict[(series.device_id, series.measure_id)] = series.values

        time_series = [
            TimeSeries(device_id=device_id, measure_id=measure_id, values=values)
            for (device_id, measure_id), values in values_dict.items()
        ]

        # now, remove values with duplicated timestamps, because the same
        # measure cannot be retrieved twice at the same timestamp
        for series in time_series:
            series.values = self.__remove_duplicates(series.values)

        return time_series

    def __remove_duplicates(
        self, values: List[TimeSeriesValue]
    ) -> List[TimeSeriesValue]:
        """
        Remove duplicates from a list of time series values
        """
        values_dict = {value.timestamp: value.value for value in values}
        return [
            TimeSeriesValue(timestamp=timestamp, value=value)
            for timestamp, value in values_dict.items()
        ]

    def __merge_options(self, options: List[TimeSeriesOptions]) -> TimeSeriesOptions:
        """
        Merge a list of options into a single one
        """
        not_none_options = [option for option in options if option is not None]

        if len(not_none_options) == 0:
            return None

        tenant = not_none_options[0].tenant
        scope = not_none_options[0].scope

        # end date is the biggest end date of all options
        end_dates = [
            option.end_date
            for option in not_none_options
            if option.end_date is not None
        ]
        end_date = max(end_dates) if len(end_dates) > 0 else None

        # start date is the smallest start date of all options
        start_dates = [
            option.start_date
            for option in not_none_options
            if option.start_date is not None
        ]
        start_date = min(start_dates) if len(start_dates) > 0 else None

        # limit is the biggest limit of all options
        # it cant be none, so no check is needed
        limit = max([option.limit for option in not_none_options])

        # aggregation is the same for all options
        aggregation = options[0].aggregation

        # order is the same for all options
        order = options[0].order

        return TimeSeriesOptions(
            start_date=start_date.isoformat() if start_date is not None else None,
            end_date=end_date.isoformat() if end_date is not None else None,
            limit=limit,
            aggregation=aggregation,
            order=order,
            tenant=tenant,
            scope=scope,
        )

    def __get_remaining_data_options(
        self, time_series: TimeSeries, options: TimeSeriesOptions
    ) -> TimeSeriesOptions:
        """
        Given the processed result of a time series, check if all requested data has been retrieved, if not, return
        a new options object with the remaining data to be retrieved.
        If all data has been retrieved, return None
        """
        if options is None:
            return None

        if (
            time_series is None
            or time_series.values is None
            or len(time_series.values) == 0
        ):
            # All data has been returned because there are no values
            return None

        num_values = len(time_series.values)

        if num_values >= options.limit:
            # All data has been returned because the limit was reached or exceeded
            return None

        # because they are retrieved from the latest to the oldest
        new_start_date = options.start_date

        new_end_date = (
            min([value.timestamp for value in time_series.values])
        ).timestamp() - 1
        new_end_date = datetime.fromtimestamp(new_end_date)

        if new_start_date is not None and new_end_date < new_start_date:
            # All data has been returned because the end date is before the start date
            return None

        new_limit = options.limit - num_values

        new_options = TimeSeriesOptions(
            start_date=(
                new_start_date.isoformat() if new_start_date is not None else None
            ),
            end_date=new_end_date.isoformat() if new_end_date is not None else None,
            limit=new_limit,
            order=options.order,
            aggregation=options.aggregation,
            tenant=options.tenant,
            scope=options.scope,
        )

        return new_options

    def __month_series_filtering(
        self, series_values: List[TimeSeriesValue], months: List[int]
    ):
        """
        Filter a list of time series values by the given months
        """
        if months is None or len(months) == 0:
            return series_values

        return [
            value for value in series_values if (value.timestamp.month - 1) in months
        ]

    def __month_day_series_filtering(
        self, series_values: List[TimeSeriesValue], month_days: List[int]
    ):
        """
        Filter a list of time series values by the given month days
        """
        if month_days is None or len(month_days) == 0:
            return series_values

        return [
            value for value in series_values if (value.timestamp.day - 1) in month_days
        ]

    def __week_day_series_filtering(
        self, series_values: List[TimeSeriesValue], week_days: List[int]
    ):
        """
        Filter a list of time series values by the given week days
        """
        if week_days is None or len(week_days) == 0:
            return series_values

        return [
            value for value in series_values if value.timestamp.weekday() in week_days
        ]

    def __hour_series_filtering(
        self, series_values: List[TimeSeriesValue], hours: List[Tuple[time, time]]
    ):
        """
        Filter a list of time series values by the given hours
        """
        if hours is None or len(hours) == 0:
            return series_values

        filtered_values = []

        for value in series_values:
            for hour in hours:
                value_time = value.timestamp.time()
                if hour[0] > hour[1]:
                    if value_time >= hour[0] or value_time <= hour[1]:
                        filtered_values.append(value)
                        break
                else:
                    if value_time >= hour[0] and value_time <= hour[1]:
                        filtered_values.append(value)
                        break

        return filtered_values

    def __date_matches_adjustment(
        self, date: datetime, adjustment: TimeScopeAdjustment
    ):
        """
        Check if a date matches the given adjustment, it gives true
        only if the date matches the adjustment and the adjustment is not None
        """

        return (
            adjustment is not None
            and adjustment.month == date.month - 1
            and adjustment.month_day == date.day - 1
        )

    def __period_adjustment_filtering(
        self,
        series_values: List[TimeSeriesValue],
        adjustments: List[TimeScopeAdjustment],
    ):
        """
        Filter a list of time series values by the given period adjustments,
        it returns two values:
        - the values that were explicitly added by the adjustments
        - the values that were filtered by the adjustments (all values that were not either explicitly added or excluded)
        """

        if adjustments is None or len(adjustments) == 0:
            return [], series_values

        extra_added_values = []
        filtered_values = []

        for value in series_values:
            for adjustment in adjustments:
                if self.__date_matches_adjustment(value.timestamp, adjustment):
                    if not adjustment.exclude:
                        extra_added_values.append(value)
                    break
            else:
                filtered_values.append(value)

        return extra_added_values, filtered_values

    def __period_series_filtering(
        self, series: TimeSeries, period: TimeScope
    ):
        """
        Filter a time series by the given period
        """

        if period is None:
            return series

        extra_added, filtered_values = self.__period_adjustment_filtering(
            series.values, period.extra
        )

        filtered_values = self.__month_series_filtering(filtered_values, period.months)
        filtered_values = self.__month_day_series_filtering(
            filtered_values, period.month_days
        )
        filtered_values = self.__week_day_series_filtering(
            filtered_values, period.week_days
        )
        filtered_values = self.__hour_series_filtering(filtered_values, period.hours)

        # add back the values that were explicitly added
        filtered_values.extend(extra_added)

        return filtered_values

    def __period_list_series_filtering(
        self, series: TimeSeries, periods: List[TimeScope]
    ):
        """
        Filter a timeseries by the given periods,
        a series passes the filter if it passes any of the periods
        """

        filtered_values = []

        for period in periods:
            filtered_values.extend(self.__period_series_filtering(series, period))

        # filter unique values
        filtered_values = self.__remove_duplicates(filtered_values)

        return TimeSeries(
            device_id=series.device_id,
            measure_id=series.measure_id,
            values=filtered_values,
        )

    def __get_query_from_options(
        self,
        entity_id: str,
        attrs,
        options: TimeSeriesOptions,
        session: requests.Session,
    ) -> requests.PreparedRequest:
        """
        Build the query from the options using the given session.
        If the request has a where clause, the entity_id is used as page anchor
        """

        query_builder = MintakaQueryBuilder(session)
        query_builder.temporalServiceUrl(self.service_url)
        query_builder.contextUrl(self.context_url)
        query_builder.ngsiLdTenant(self.tenant)
        query_builder.filterAttrs(attrs)

        if options is None:
            return query_builder

        start_date = options.start_date
        if start_date is not None:
            query_builder.startDateTime(start_date)

        end_date = options.end_date
        if end_date is not None:
            query_builder.endDateTime(end_date)

        if start_date is None and end_date is None:
            end_date = datetime.now() + timedelta(days=2)
            end_date = query_builder.endDateTime(end_date)

        limit = options.limit
        if limit is not None:
            query_builder.lastN(limit)

        where_clause = options.where
        if where_clause is not None:
            query_builder.add_conditions(where_clause)
            query_builder.set_page_size(self.default_entity_page_size)
            query_builder.set_page_anchor(entity_id)
        else:
            query_builder.filterEntityId(entity_id)

        query, _ = query_builder.build()

        return query

    def __transform_ngsi_ld_response(
        self, response: dict, requested_measures: List[str]
    ) -> List[TimeSeries]:
        """
        Transform the response from mintaka to a list of time series
        """

        # Received response from mintaka, must be transformed to TimeSeries
        # a single response may contain multiple time series (one for each attribute)

        time_series_list = []

        entity_id = response.get("id")

        if entity_id is None:
            logging.error("Entity id not found in response, skipping")
            return time_series_list

        for measure in requested_measures:
            attr = response.get(measure)

            if attr is None:
                continue

            time_series = TimeSeries(
                device_id=entity_id,
                measure_id=measure,
                values=self.__attr_to_time_series_values(attr),
            )

            time_series_list.append(time_series)

        return time_series_list

    def __attr_to_time_series_values(
        self, attr: Union[dict, List]
    ) -> List[TimeSeriesValue]:
        """
        Transform a mintaka attribute to a list of time series values.
        This is because an attribute could be a dict or a list. It is a dict if it is a single value,
        and a list if the attribute had multiple values.
        """

        # if it is not a list, it is a single value, convert to list
        if not isinstance(attr, list):
            attr = [attr]

        time_series_values = []

        for attr_value in attr:
            value = get_value_property_from_normalized_attribute(attr_value)
            timestamp = get_temporal_property_from_normalized_attribute(attr_value)

            if value is None or timestamp is None:
                continue

            time_series_values.append(
                TimeSeriesValue(
                    timestamp=timestamp.isoformat(),
                    value=value,
                )
            )

        return time_series_values
