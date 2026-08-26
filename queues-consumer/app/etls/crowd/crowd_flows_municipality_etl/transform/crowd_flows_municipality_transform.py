import pandas as pd
from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from schemas.crowd_flows_municipality_request_schema import (
    CrowdFlowsMunicipalityRequest,
)
import db.realtime as realtime_db
from db import deps
import dateutil.parser


class CrowdFlowsMunicipalityTransform:

    def __init__(
        self,
        request: CrowdFlowsMunicipalityRequest,
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

        visitor_data = visitor_data[
            visitor_data["origin_entityid"] != visitor_data["entityid"]
        ]

        return visitor_data

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

    def __add_time_difference(self):
        """
        Adds a 'time_difference' column to the DataFrame.
        - Default value is None.
        - Where 'origin_timeinstant' is not null, it calculates the difference between 'timeinstant' and 'origin_timeinstant'.

        Args:
            df (pd.DataFrame): Input dataframe with 'timeinstant' and 'origin_timeinstant' columns.

        Returns:
            pd.DataFrame: DataFrame with the new 'time_difference' column.
        """
        # Ensure timestamps are in datetime format
        self.processed_data["timeinstant"] = self.processed_data["timeinstant"].apply(
            lambda x: dateutil.parser.parse(x) if isinstance(x, str) else x
        )
        self.processed_data["origin_timeinstant"] = self.processed_data[
            "origin_timeinstant"
        ].apply(lambda x: dateutil.parser.parse(x) if isinstance(x, str) else x)

        self.processed_data["timeinstant"] = pd.to_datetime(
            self.processed_data["timeinstant"]
        )
        self.processed_data["origin_timeinstant"] = pd.to_datetime(
            self.processed_data["origin_timeinstant"], errors="coerce"
        )

        # Add 'time_difference' column
        self.processed_data["time_difference"] = None

        # Compute time difference where 'origin_timeinstant' is not null
        self.processed_data.loc[
            self.processed_data["origin_timeinstant"].notna(), "time_difference"
        ] = (
            self.processed_data["timeinstant"]
            - self.processed_data["origin_timeinstant"]
        )

        return self.processed_data

    def __calculate_transits_duration_and_count(self, class_name=""):
        """
        Function to calculate transits duration by classification
        """
        if class_name != "":
            data = self.processed_data[self.processed_data["visitortype"] == class_name]
        else:
            data = self.processed_data

        average_time = (
            data.groupby(["origin_entityid", "entityid"])["time_difference"]
            .mean()
            .reset_index()
            .rename(
                columns={
                    "time_difference": f"{class_name.lower()}averagetransitduration"
                }
            )
        )

        min_time = (
            data.groupby(["origin_entityid", "entityid"])["time_difference"]
            .min()
            .reset_index()
            .rename(
                columns={
                    "time_difference": f"{class_name.lower()}minimumtransitduration"
                }
            )
        )
        max_time = (
            data.groupby(["origin_entityid", "entityid"])["time_difference"]
            .max()
            .reset_index()
            .rename(
                columns={
                    "time_difference": f"{class_name.lower()}maximumtransitduration"
                }
            )
        )

        sum_transits = (
            data.groupby(["origin_entityid", "entityid"])["time_difference"]
            .count()
            .reset_index()
            .rename(columns={"time_difference": f"{class_name.lower()}count"})
        )

        merged_time = pd.merge(
            average_time, min_time, how="left", on=["origin_entityid", "entityid"]
        )

        merged_time = pd.merge(
            merged_time, max_time, how="left", on=["origin_entityid", "entityid"]
        )

        merged_time = pd.merge(
            merged_time, sum_transits, how="left", on=["origin_entityid", "entityid"]
        )

        return merged_time

    def __calculate_transits_duration_with_classification(self):
        if self.use_classification:
            result_tourist = self.__calculate_transits_duration_and_count("Tourist")

            result_resident = self.__calculate_transits_duration_and_count("Resident")

            result_short_term = self.__calculate_transits_duration_and_count(
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

    def __calculate_transits_duration(self):
        self.processed_data = self.__add_time_difference()

        self.result = self.__calculate_transits_duration_and_count()

        self.result = self.__calculate_transits_duration_with_classification()

        return self.result

    def __aggregate_by_origin_entity(self):
        """
        Function to aggregate data by origin entity
        """
        # Aggregate data by entityid, considering both origin and destination
        df = self.result.copy()

        grouped_df = pd.concat(
            [
                df.drop(columns=["entityid"], errors="ignore").rename(
                    columns={"origin_entityid": "entityid"}
                ),
                df.drop(columns=["origin_entityid"], errors="ignore"),
            ]
        )

        grouped = (
            grouped_df.groupby("entityid")
            .agg(
                {
                    "averagetransitduration": "mean",
                    "minimumtransitduration": "min",
                    "maximumtransitduration": "max",
                    "count": "sum",
                    "touristaveragetransitduration": "mean",
                    "touristminimumtransitduration": "min",
                    "touristmaximumtransitduration": "max",
                    "touristcount": "sum",
                    "residentaveragetransitduration": "mean",
                    "residentminimumtransitduration": "min",
                    "residentmaximumtransitduration": "max",
                    "residentcount": "sum",
                    "shorttermvisitoraveragetransitduration": "mean",
                    "shorttermvisitorminimumtransitduration": "min",
                    "shorttermvisitormaximumtransitduration": "max",
                    "shorttermvisitorcount": "sum",
                }
            )
            .reset_index()
        )

        grouped["origin_entityid"] = grouped["entityid"]

        self.result = pd.concat([self.result, grouped], ignore_index=True)

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

        if self.processed_data.empty:
            return pd.DataFrame()

        self.classified_visitors = self.__classify_visitors(self.processed_data)

        self.result = self.__calculate_transits_duration()

        self.result = self.__aggregate_by_origin_entity()

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
