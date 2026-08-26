import pandas as pd
from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from schemas.crowd_process_visitors_request_schema import (
    ProcessVisitorsRequest,
)
import db.realtime as realtime_db
from db import deps
import dateutil.parser


class ProcessVisitorsTransform:

    def __init__(
        self,
        request: ProcessVisitorsRequest,
        extract_output: dict,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        # DB connections
        self.main_db = main_db
        self.realtime_db = realtime_db

        # Extract output
        self.visitors = extract_output["visitors"]
        self.df_raw = extract_output["df_raw"]
        self.previous_visitor_types = extract_output["previous_visitor_types"]

        # Request
        self.mode = request.mode
        self.aggregation_mode = request.aggregation_mode

        # Constants
        self.use_classification = True

    def __calculate_visitor_flow(self, visitor):
        """
        Function to calculate the flow for a visitor
        """
        visitor_data = self.df_raw[self.df_raw["visitorid"] == visitor]

        visitor_data = visitor_data.sort_values("timeinstant").reset_index(drop=True)

        visitor_data["origin_timeinstant"] = visitor_data["timeinstant"].shift(1)
        visitor_data["origin_entityid"] = visitor_data["entityid"].shift(1)

        visitor_data = visitor_data.sort_values(
            by=["visitorid", "entityid", "timeinstant"]
        )

        # Identify separate visits by detecting when a visitor returns to the same place after leaving
        visitor_data["new_visit"] = (
            visitor_data["entityid"] != visitor_data["origin_entityid"]
        ) | (visitor_data["origin_entityid"].isna())

        # Assign unique visit IDs
        visitor_data["visit_id"] = visitor_data["new_visit"].cumsum()

        visitor_data.loc[
            visitor_data["origin_timeinstant"].isna(), "origin_timeinstant"
        ] = visitor_data["timeinstant"]

        visitor_data["origin_timeinstant"] = visitor_data["origin_timeinstant"].apply(
            lambda x: dateutil.parser.parse(x) if isinstance(x, str) else x
        )

        visitor_data["origin_timeinstant"] = pd.to_datetime(
            visitor_data["origin_timeinstant"]
        )

        visitor_data["timeinstant"] = visitor_data["timeinstant"].apply(
            lambda x: dateutil.parser.parse(x) if isinstance(x, str) else x
        )

        visitor_data["timeinstant"] = pd.to_datetime(visitor_data["timeinstant"])

        agg_funcs = {col: "first" for col in visitor_data.columns if col != "visit_id"}

        agg_funcs["origin_timeinstant"] = "min"
        agg_funcs["timeinstant"] = "max"

        unique_visits = visitor_data.groupby("visit_id").agg(agg_funcs).reset_index()

        unique_visits["duration"] = (
            unique_visits["timeinstant"] - unique_visits["origin_timeinstant"]
        )

        return unique_visits

    def __calculate_visitor_count_by_class_name(self, class_name):
        count = (
            self.processed_data[self.processed_data["visitortype"] == class_name]
            .groupby("entityid")["visitorid"]
            .count()
            .rename(f"{class_name.lower()}visits")
        )

        return count

    def __classify_visitors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Classifies visitors as 'Resident' or 'Tourist' based on their presence over time.

        Criteria:
        - If a visitor appears on more than 3 different days, they are classified as 'Resident'.
        - If a visitor appears only on 1-2 days but spends more than 6 hours in total, they are classified as 'Tourist'.
        - Otherwise, they are classified as 'ShortTermVisitor' (optional).

        Args:
            df (pd.DataFrame): DataFrame containing visitor records with 'timeinstant' and 'visitorid'.


        Returns:
            pd.DataFrame: The input DataFrame with a new column 'visitortype' assigned.
        """

        # Classification logic
        def classify_visitor(vid):
            visitor_data = self.previous_visitor_types.get(vid, None)

            if visitor_data:
                return visitor_data
            else:
                return "ShortTermVisitor"

        df["visitortype"] = df["visitorid"].map(classify_visitor)

        return df

    def __calculate_visits_count_with_classification(self):
        if self.use_classification:
            tourist_visits_count = self.__calculate_visitor_count_by_class_name(
                "Tourist"
            )

            resident_visits_count = self.__calculate_visitor_count_by_class_name(
                "Resident"
            )

            short_term_visits_count = self.__calculate_visitor_count_by_class_name(
                "ShortTermVisitor"
            )

            self.visits_count = pd.merge(
                self.visits_count, tourist_visits_count, how="left", on="entityid"
            )

            self.visits_count = pd.merge(
                self.visits_count, resident_visits_count, how="left", on="entityid"
            )

            self.visits_count = pd.merge(
                self.visits_count,
                short_term_visits_count,
                how="left",
                on="entityid",
            )

        return self.visits_count

    def __calculate_unique_visitor_counts(self):
        """
        Calculates total and classified unique visitors per entity
        """
        # Total unique visitors per entity
        unique_visitors = (
            self.processed_data.groupby("entityid")["visitorid"]
            .nunique()
            .reset_index()
            .rename(columns={"visitorid": "unique_visitors"})
        )

        if self.use_classification:

            def unique_by_class(class_name):
                return (
                    self.processed_data[
                        self.processed_data["visitortype"] == class_name
                    ]
                    .groupby("entityid")["visitorid"]
                    .nunique()
                    .reset_index()
                    .rename(
                        columns={"visitorid": f"{class_name.lower()}_unique_visitors"}
                    )
                )

            tourist_uv = unique_by_class("Tourist")
            resident_uv = unique_by_class("Resident")
            short_term_uv = unique_by_class("ShortTermVisitor")

            unique_visitors = pd.merge(
                unique_visitors, tourist_uv, how="left", on="entityid"
            )
            unique_visitors = pd.merge(
                unique_visitors, resident_uv, how="left", on="entityid"
            )
            unique_visitors = pd.merge(
                unique_visitors, short_term_uv, how="left", on="entityid"
            )

        return unique_visitors

    def __calculate_visits_count(self):
        self.visits_count = (
            self.processed_data.groupby("entityid")["visitorid"]
            .count()
            .rename("visits")
        )

        self.visits_count = self.__calculate_visits_count_with_classification()

        return self.visits_count

    def __calculate_visits_duration_and_count(self, class_name=""):
        """
        Function to calculate visits duration by classification
        """
        if class_name != "":
            data = self.processed_data[self.processed_data["visitortype"] == class_name]
        else:
            data = self.processed_data

        data = data[data["origin_entityid"] == data["entityid"]]

        average_time = (
            data.groupby(["origin_entityid", "entityid"])["duration"]
            .mean()
            .reset_index()
            .rename(columns={"duration": f"{class_name.lower()}averagevisitduration"})
        )

        min_time = (
            data.groupby(["origin_entityid", "entityid"])["duration"]
            .min()
            .reset_index()
            .rename(columns={"duration": f"{class_name.lower()}minimumvisitduration"})
        )
        max_time = (
            data.groupby(["origin_entityid", "entityid"])["duration"]
            .max()
            .reset_index()
            .rename(columns={"duration": f"{class_name.lower()}maximumvisitduration"})
        )

        merged_time = pd.merge(
            average_time, min_time, how="left", on=["origin_entityid", "entityid"]
        )

        merged_time = pd.merge(
            merged_time, max_time, how="left", on=["origin_entityid", "entityid"]
        )

        return merged_time

    def __calculate_visits_duration_with_classification(self):
        if self.use_classification:
            result_tourist = self.__calculate_visits_duration_and_count("Tourist")

            result_resident = self.__calculate_visits_duration_and_count("Resident")

            result_short_term = self.__calculate_visits_duration_and_count(
                "ShortTermVisitor"
            )

            self.result = pd.merge(
                self.result,
                result_tourist,
                how="left",
                on=["origin_entityid", "entityid"],
            )

            self.result = pd.merge(
                self.result,
                result_resident,
                how="left",
                on=["origin_entityid", "entityid"],
            )

            self.result = pd.merge(
                self.result,
                result_short_term,
                how="left",
                on=["origin_entityid", "entityid"],
            )

        return self.result

    def __calculate_visits_duration(self):
        # self.processed_data = self.__add_time_difference()

        self.result = self.__calculate_visits_duration_and_count()

        self.result = self.__calculate_visits_duration_with_classification()

        self.result = pd.merge(
            self.result, self.visits_count, how="left", on="entityid"
        )

        self.result = self.result.drop(columns=["origin_entityid"], errors="ignore")

        unique_visitor_counts = self.__calculate_unique_visitor_counts()

        self.result = pd.merge(
            self.result, unique_visitor_counts, how="left", on="entityid"
        )

        return self.result

    def __calculate_visitor_flows(self):
        """
        Function to calculate visitor flows
        """
        # For each visitor, calculate the flow
        self.processed_data = pd.DataFrame()

        visitor_data_list = [
            self.__calculate_visitor_flow(visitor) for visitor in self.visitors
        ]

        self.processed_data = pd.concat(visitor_data_list, ignore_index=True)

        self.classified_visitors = self.__classify_visitors(self.processed_data)

        self.visits_count = self.__calculate_visits_count()

        self.result = self.__calculate_visits_duration()

        return self.result

    def transform(self):
        if self.mode == "tourism":
            self.result = self.__calculate_visitor_flows()
        else:
            logging.error("Flow mode not supported.")

            return False

        return {
            "result": self.result,
        }
