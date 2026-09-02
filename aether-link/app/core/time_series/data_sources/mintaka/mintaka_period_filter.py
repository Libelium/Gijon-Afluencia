from datetime import datetime, time
from typing import List, Tuple

from aether_pylib.time_series.time_series import TimeSeries, TimeSeriesValue
from aether_pylib.time_series.time_scope import TimeScope, TimeScopeAdjustment


class MintakaPeriodFilter:
    """Period-based filtering of time-series values (months, month days, week days,
    hour ranges and explicit TimeScope adjustments).

    A pure, stateless collaborator extracted from MintakaDataSource: the calendar logic
    lived intertwined with the HTTP/pagination code, and moving it here keeps each side
    focused. The public entry point is ``filter_series_list``; MintakaDataSource keeps a
    thin delegating method that forwards to it.
    """

    def filter_series_list(
        self, series: TimeSeries, periods: List[TimeScope]
    ) -> TimeSeries:
        """
        Filter a timeseries by the given periods,
        a series passes the filter if it passes any of the periods
        """

        filtered_values = []

        for period in periods:
            filtered_values.extend(self._filter_series(series, period))

        # filter unique values
        filtered_values = self._remove_duplicates(filtered_values)

        return TimeSeries(
            device_id=series.device_id,
            measure_id=series.measure_id,
            values=filtered_values,
        )

    def _filter_series(self, series: TimeSeries, period: TimeScope):
        """
        Filter a time series by the given period
        """

        if period is None:
            return series

        extra_added, filtered_values = self._adjustment_filtering(
            series.values, period.extra
        )

        filtered_values = self._month_filtering(filtered_values, period.months)
        filtered_values = self._month_day_filtering(
            filtered_values, period.month_days
        )
        filtered_values = self._week_day_filtering(
            filtered_values, period.week_days
        )
        filtered_values = self._hour_filtering(filtered_values, period.hours)

        # add back the values that were explicitly added
        filtered_values.extend(extra_added)

        return filtered_values

    def _month_filtering(
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

    def _month_day_filtering(
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

    def _week_day_filtering(
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

    def _hour_filtering(
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

    def _date_matches_adjustment(
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

    def _adjustment_filtering(
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
                if self._date_matches_adjustment(value.timestamp, adjustment):
                    if not adjustment.exclude:
                        extra_added_values.append(value)
                    break
            else:
                filtered_values.append(value)

        return extra_added_values, filtered_values

    def _remove_duplicates(
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
