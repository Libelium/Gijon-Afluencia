import pandas as pd
from sqlalchemy.orm import Session
from datetime import timedelta
from schemas.crowd_process_visitors_request_schema import (
    ProcessVisitorsRequest,
)
from etls.crowd.base_crowd_entity_load import BaseCrowdEntityLoad

# Retained as the module-level monkeypatch surface the load tests rely on: the shared
# publishing pipeline lives in BaseCrowdEntityLoad but references these same module
# objects, so patching them here (e.g. crowd_process_visitors_load.iota_helper) still
# intercepts the calls the base class makes.
import helpers.aether_link.aether_link_helper as aether_link_helper  # noqa: F401
import models.crud.crud_tenant_scope as crud_tenant_scope  # noqa: F401
import models.crud.crud_preferences as crud_preferences  # noqa: F401
from helpers.iota import iota_helper  # noqa: F401


class ProcessVisitorsLoad(BaseCrowdEntityLoad):

    def __init__(
        self,
        request: ProcessVisitorsRequest,
        transform_output: dict,
        main_db: Session,
        realtime_db: Session,
    ):
        # DB Sessions
        self.main_db = main_db
        self.realtime_db = realtime_db

        # Transform Output
        self.result = transform_output["result"]

        # Request
        self.entities = request.entities
        self.start_date = request.start_date
        self.end_date = request.end_date
        self.mode = request.mode
        self.user_id = request.user_id

        # Constants
        self.use_classification = True


    def _generate_entity_payload(self, data: dict) -> dict:
        payload = []

        for flow in data:
            flow_entity_id = self._get_entity_id_from_urn(flow["entity"])

            flow_id = f"{flow_entity_id}"

            new_flow = {
                "entityId": flow_id,
                "averageVisitDuration": (
                    flow["averageVisitDuration"].total_seconds()
                    if isinstance(flow["averageVisitDuration"], timedelta)
                    else None
                ),
                "minimumVisitDuration": (
                    flow["minimumVisitDuration"].total_seconds()
                    if isinstance(flow["minimumVisitDuration"], timedelta)
                    else None
                ),
                "maximumVisitDuration": (
                    flow["maximumVisitDuration"].total_seconds()
                    if isinstance(flow["maximumVisitDuration"], timedelta)
                    else None
                ),
                "visits": flow["visits"] if flow["visits"] else 0,
                "uniqueVisitors": (
                    flow["uniqueVisitors"] if flow["uniqueVisitors"] else 0
                ),
                "touristAverageVisitDuration": (
                    flow["touristAverageVisitDuration"].total_seconds()
                    if isinstance(flow["touristAverageVisitDuration"], timedelta)
                    else None
                ),
                "touristMinimumVisitDuration": (
                    flow["touristMinimumVisitDuration"].total_seconds()
                    if isinstance(flow["touristMinimumVisitDuration"], timedelta)
                    else None
                ),
                "touristMaximumVisitDuration": (
                    flow["touristMaximumVisitDuration"].total_seconds()
                    if isinstance(flow["touristMaximumVisitDuration"], timedelta)
                    else None
                ),
                "touristVisits": (
                    flow["touristVisits"] if flow["touristVisits"] else 0
                ),
                "touristUniqueVisitors": (
                    flow["touristUniqueVisitors"]
                    if flow["touristUniqueVisitors"]
                    else 0
                ),
                "residentAverageVisitDuration": (
                    flow["residentAverageVisitDuration"].total_seconds()
                    if isinstance(flow["residentAverageVisitDuration"], timedelta)
                    else None
                ),
                "residentMinimumVisitDuration": (
                    flow["residentMinimumVisitDuration"].total_seconds()
                    if isinstance(flow["residentMinimumVisitDuration"], timedelta)
                    else None
                ),
                "residentMaximumVisitDuration": (
                    flow["residentMaximumVisitDuration"].total_seconds()
                    if isinstance(flow["residentMaximumVisitDuration"], timedelta)
                    else None
                ),
                "residentVisits": (
                    flow["residentVisits"] if flow["residentVisits"] else 0
                ),
                "residentUniqueVisitors": (
                    flow["residentUniqueVisitors"]
                    if flow["residentUniqueVisitors"]
                    else 0
                ),
                "shortTermVisitorAverageVisitDuration": (
                    flow["shortTermVisitorAverageVisitDuration"].total_seconds()
                    if isinstance(
                        flow["shortTermVisitorAverageVisitDuration"], timedelta
                    )
                    else None
                ),
                "shortTermVisitorMinimumVisitDuration": (
                    flow["shortTermVisitorMinimumVisitDuration"].total_seconds()
                    if isinstance(
                        flow["shortTermVisitorMinimumVisitDuration"], timedelta
                    )
                    else None
                ),
                "shortTermVisitorMaximumVisitDuration": (
                    flow["shortTermVisitorMaximumVisitDuration"].total_seconds()
                    if isinstance(
                        flow["shortTermVisitorMaximumVisitDuration"], timedelta
                    )
                    else None
                ),
                "shortTermVisitorVisits": (
                    flow["shortTermVisitorVisits"]
                    if flow["shortTermVisitorVisits"]
                    else 0
                ),
                "shortTermVisitorUniqueVisitors": (
                    flow["shortTermVisitorUniqueVisitors"]
                    if flow["shortTermVisitorUniqueVisitors"]
                    else 0
                ),
                "TimeInstant": self.start_date.isoformat(),
                "startDate": self.start_date.isoformat(),
                "endDate": self.end_date.isoformat(),
            }

            payload.append(new_flow)

        return payload

    def _process_to_fiware(self, df: pd.DataFrame) -> dict:
        """
        Function to process data to Fiware and returns a json
        """
        # Rename columns to match required JSON format
        mapping = {
            "entityid": "entity",
            "averagevisitduration": "averageVisitDuration",
            "minimumvisitduration": "minimumVisitDuration",
            "maximumvisitduration": "maximumVisitDuration",
            "visits": "visits",
            "touristaveragevisitduration": "touristAverageVisitDuration",
            "touristminimumvisitduration": "touristMinimumVisitDuration",
            "touristmaximumvisitduration": "touristMaximumVisitDuration",
            "touristvisits": "touristVisits",
            "residentaveragevisitduration": "residentAverageVisitDuration",
            "residentminimumvisitduration": "residentMinimumVisitDuration",
            "residentmaximumvisitduration": "residentMaximumVisitDuration",
            "residentvisits": "residentVisits",
            "shorttermvisitoraveragevisitduration": "shortTermVisitorAverageVisitDuration",
            "shorttermvisitorminimumvisitduration": "shortTermVisitorMinimumVisitDuration",
            "shorttermvisitormaximumvisitduration": "shortTermVisitorMaximumVisitDuration",
            "shorttermvisitorvisits": "shortTermVisitorVisits",
            "unique_visitors": "uniqueVisitors",
            "tourist_unique_visitors": "touristUniqueVisitors",
            "resident_unique_visitors": "residentUniqueVisitors",
            "shorttermvisitor_unique_visitors": "shortTermVisitorUniqueVisitors",
        }

        # Rename the columns in the dataframe
        df = df.rename(columns=mapping)

        # Convert dataframe to list of dictionaries
        js = df.to_dict(orient="records")

        # Generate the entity payload
        self.iota_payload = self._generate_entity_payload(js)

        return self.iota_payload
