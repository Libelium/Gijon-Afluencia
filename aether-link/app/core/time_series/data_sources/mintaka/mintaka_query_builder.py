from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Self
from app.core.config.logging import appLogging as logging

import requests

from aether_pylib.time_series.time_series_options import (
    WhereClause,
    WhereClauseOperation,
    WhereClauseOperator,
)


class NgsiLdTroeTimeRel(Enum):
    """
    Enum for the time relation parameter of the NGSI-LD temporal query
    """

    BEFORE = "before"
    AFTER = "after"
    BETWEEN = "between"


@dataclass
class NgsiLdTroeRequest:
    """
    Class to represent a NGSI-LD temporal query. It should be something global, but
    it is only used in the Mintaka query builder, and it turns out that noone follows
    the same NGSILD-Temporal API standard.
    """

    entity_id: str = None
    attrs: List[str] = None
    last_n: int = None
    time_rel: NgsiLdTroeTimeRel = None
    time_at: str = None
    end_time_at: str = None
    time_property: str = None
    q: str = None
    page_size: int = None
    page_anchor: str = None

    # communication params
    temporal_service_url: str = None
    ngsi_ld_tenant: str = None
    context_url: str = None


class MintakaQueryBuilder:
    """
    Query builder for the NGSI-LD temporal query on mintaka.
    It is used to build the query over a session (if given)
    """

    def __init__(self, session=requests.Session()):
        """
        Builder. Default session if not given
        """
        self.ngsi_ld_troe_request = NgsiLdTroeRequest()
        self.ngsi_ld_troe_request.attrs = []
        self.ngsi_ld_troe_request.q = None
        self.ngsi_ld_troe_request.entity_id = None
        self.session = session

    def temporalServiceUrl(self, temporal_service_url: str) -> Self:
        """
        Mintaka url
        """
        self.ngsi_ld_troe_request.temporal_service_url = temporal_service_url
        return self

    def contextUrl(self, context_url: str) -> Self:
        """
        Context file url
        """
        self.ngsi_ld_troe_request.context_url = context_url
        return self

    def ngsiLdTenant(self, ngsi_ld_tenant: str) -> Self:
        """
        NGSI-LD tenant
        """
        self.ngsi_ld_troe_request.ngsi_ld_tenant = ngsi_ld_tenant
        return self

    def filterEntityId(self, entity_id: str) -> Self:
        """
        A query only applies to one entity, so this is the entity id to query for
        """
        self.ngsi_ld_troe_request.entity_id = entity_id
        return self

    def filterAttrs(self, attrs: List[str]) -> Self:
        """
        Attributes to query for
        """
        self.ngsi_ld_troe_request.attrs.extend(attrs)
        return self

    def lastN(self, last_n: int) -> Self:
        """
        Limit data results
        """
        self.ngsi_ld_troe_request.last_n = last_n
        return self

    def startDateTime(self, start_date_time: datetime) -> Self:
        """
        Start date time
        """
        self.ngsi_ld_troe_request.time_at = start_date_time
        return self

    def endDateTime(self, end_date_time: datetime) -> Self:
        """
        End date time
        """
        self.ngsi_ld_troe_request.end_time_at = end_date_time
        return self

    def timeProperty(self, time_property: str) -> Self:
        """
        Time property for the query. You might want to query for a specific time property
        """
        self.ngsi_ld_troe_request.time_property = time_property
        return self

    def __where_clause_condition_to_q_string(self, condition: List[str]) -> str:
        """
        Convert where clause condition to q string
        NOTE: this function is optimized only for 2 operand operators, be careful
        when adding a new one
        """

        if condition[1] == WhereClauseOperator.EQ.value:
            if isinstance(condition[2], str):
                return f"{condition[0]}==\"{condition[2]}\""

        logging.error(f"Unsupported operator: {condition[1]}")

        return None

    def __join_conditions(
        self, conditions: List[str], operator: WhereClauseOperator
    ) -> str:
        """
        Join conditions with the given operator, using the NGSI-LD TROE query syntax
        format
        """
        if operator == WhereClauseOperation.AND:
            return ";".join(conditions)
        else:
            logging.error(f"Unsupported operator: {operator}")

        return None

    def add_conditions(self, where_clause: WhereClause) -> Self:
        """
        Add conditions to the query, the condition must be.
        Multiple calls to this method will add conditions with the AND operator
        """
        conditions = []

        for condition in where_clause.conditions:
            conditions.append(self.__where_clause_condition_to_q_string(condition))

        query_string = self.__join_conditions(conditions, where_clause.operation)

        if self.ngsi_ld_troe_request.q is not None:
            self.ngsi_ld_troe_request.q += ";" + query_string
        else:
            self.ngsi_ld_troe_request.q = query_string

        return self

    def set_page_size(self, page_size: int) -> Self:
        """
        Set page size
        """
        self.ngsi_ld_troe_request.page_size = page_size
        return self

    def set_page_anchor(self, page_anchor: str) -> Self:
        """
        Set page anchor
        """
        self.ngsi_ld_troe_request.page_anchor = page_anchor
        return self

    def __build_time_params(self) -> dict:
        """
        Builds url params related to time restrictions for the query
        """
        if (
            self.ngsi_ld_troe_request.time_at is not None
            and self.ngsi_ld_troe_request.end_time_at is not None
        ):
            return {
                "timerel": NgsiLdTroeTimeRel.BETWEEN.value,
                "timeAt": self.ngsi_ld_troe_request.time_at.isoformat(),
                "endTimeAt": self.ngsi_ld_troe_request.end_time_at.isoformat(),
            }

        if (
            self.ngsi_ld_troe_request.time_at is not None
            and self.ngsi_ld_troe_request.end_time_at is None
        ):
            return {
                "timerel": NgsiLdTroeTimeRel.AFTER.value,
                "timeAt": self.ngsi_ld_troe_request.time_at.isoformat(),
            }

        if (
            self.ngsi_ld_troe_request.time_at is None
            and self.ngsi_ld_troe_request.end_time_at is not None
        ):
            return {
                "timerel": NgsiLdTroeTimeRel.BEFORE.value,
                "timeAt": self.ngsi_ld_troe_request.end_time_at.isoformat(),
            }

        return {}

    def session(self, session: requests.Session) -> Self:
        """
        Set session
        """
        self.session = session
        return self

    def __build_params(self) -> dict:
        """
        Builds url params for the http query
        """
        params = {}

        if (
            self.ngsi_ld_troe_request.attrs is None
            or len(self.ngsi_ld_troe_request.attrs) > 0
        ):
            params["attrs"] = self.ngsi_ld_troe_request.attrs

        if self.ngsi_ld_troe_request.last_n is not None:
            params["lastN"] = self.ngsi_ld_troe_request.last_n

        if self.ngsi_ld_troe_request.time_property is not None:
            params["timeProperty"] = self.ngsi_ld_troe_request.time_property

        if self.ngsi_ld_troe_request.q is not None:
            params["q"] = self.ngsi_ld_troe_request.q

        if self.ngsi_ld_troe_request.page_size is not None:
            params["pageSize"] = self.ngsi_ld_troe_request.page_size
        
        if self.ngsi_ld_troe_request.page_anchor is not None:
            params["pageAnchor"] = self.ngsi_ld_troe_request.page_anchor

        params.update(self.__build_time_params())

        return params

    def __build_context_link_header(self, context_url: str) -> str:
        """
        Build context link header value
        """
        return f'<{context_url}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'

    def __build_headers(self) -> dict:
        """
        Builds all headers for the http query
        """
        headers = {}

        headers["Accept"] = "*/*"

        if self.ngsi_ld_troe_request.context_url is not None:
            if self.ngsi_ld_troe_request.ngsi_ld_tenant is not None:
                headers["NGSILD-Tenant"] = self.ngsi_ld_troe_request.ngsi_ld_tenant

            if self.ngsi_ld_troe_request.context_url is not None:
                headers["Link"] = self.__build_context_link_header(
                    self.ngsi_ld_troe_request.context_url
                )

        return headers

    def build(self) -> (requests.PreparedRequest, requests.Session):
        """
        Build the request over the session
        """

        query_url_base = (
            self.ngsi_ld_troe_request.temporal_service_url + "/temporal/entities"
        )

        has_query_param = (
            self.ngsi_ld_troe_request.q is not None
            and len(self.ngsi_ld_troe_request.q) > 0
        )

        query_url = (
            query_url_base
            if has_query_param
            else (f"{query_url_base}/{self.ngsi_ld_troe_request.entity_id}")
        )

        return (
            self.session.prepare_request(
                requests.Request(
                    "GET",
                    query_url,
                    params=self.__build_params(),
                    headers=self.__build_headers(),
                )
            ),
            self.session,
        )
