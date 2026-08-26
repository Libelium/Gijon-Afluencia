import pandas as pd
from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from schemas.crowd_unique_visitors_request_schema import (
    CrowdUniqueVisitorsRequest,
)
import db.realtime as realtime_db
from db import deps
import dateutil.parser
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from models.crud.crud_crowd_visitors import get_user_crowd_visitor, get_user_crowd_visitors_updated_at, get_user_crowd_visitors_created_at
from helpers.crowd.crowd_utils import classify_visitors
class UniqueVisitorsTransform:

    def __init__(
        self,
        request: CrowdUniqueVisitorsRequest,
        extract_output: dict,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        # DB connections
        self.main_db = main_db
        self.realtime_db = realtime_db

        # Request
        self.aggregation_mode = request.aggregation_mode
        self.user_id = request.user_id

        # Extract output
        self.df_raw = extract_output["df_raw"]
        self.start_date = extract_output["start_date"]
        self.end_date = extract_output["end_date"]

        self.previous_visitors = get_user_crowd_visitor(self.main_db, self.user_id)

        self.new_visitor_counts = {}

    def _generate_relative_time_bins(self) -> list:
        """
        Generate a list of dates counting backwards from end_date
        to start_date
        """
        
        bins = [self.end_date]
        current_date = self.end_date
        
        while current_date > self.start_date:
            if self.aggregation_mode == 'Daily':
                current_date -= timedelta(days=1)
            elif self.aggregation_mode == 'Weekly':
                current_date -= timedelta(weeks=1)
            elif self.aggregation_mode == 'Monthly':
                current_date -= relativedelta(months=1)
            else:
                break 

            bins.append(current_date)
        
        bins = sorted(list(set(bins)))
        
        if len(bins) < 2:
            logging.warning(f"Could not generate intervals for dates {self.start_date} to {self.end_date}. Using total aggregation.")
            return []
            
        return bins

    def __get_current_visitor_sets(self) -> tuple[set, set]:
        """
        Get sets of current residents and tourists from classified visitors.
        Returns:
            tuple: (current_residents, current_tourists)
        """
        current_residents = set(
            self.classified_visitors[
                self.classified_visitors['visitortype'] == 'Resident'
            ]['visitorid']
        )
        current_tourists = set(
            self.classified_visitors[
                self.classified_visitors['visitortype'] == 'Tourist'
            ]['visitorid']
        )

        return current_residents, current_tourists

    def __get_updated_visitor_ids(self) -> set:
        """
        Get set of visitor IDs that were updated after start_date.
        Returns:
            set: Set of visitor IDs that have updated_at >= start_date
        """
        updated_visitors = get_user_crowd_visitors_updated_at(self.main_db,self.user_id,self.start_date)

        return set(v.visitor_id for v in updated_visitors)

    def __get_created_visitor_ids(self) -> set:
        """
        Get set of visitor IDs that were created after start_date.
        Returns:
            set: Set of visitor IDs that have created_at >= start_date
        """
        created_visitors = get_user_crowd_visitors_created_at(self.main_db,self.user_id,self.start_date)

        return set(v.visitor_id for v in created_visitors)

    def __calculate_new_unique_visitor_counts(self, current_residents: set, current_tourists: set, created_visitor_ids: set, updated_visitor_ids: set, all_db_visitor_ids: set) -> dict:
        """
        Calculate counts of new unique visitors.

        - newUniqueVisitors: All visitors with created_at >= start_date
        - newResidentUniqueVisitors: Residents with updated_at >= start_date OR not in DB yet
        - newTouristUniqueVisitors: Tourists with updated_at >= start_date OR not in DB yet

        Args:
            current_residents: Set of current resident IDs from classification
            current_tourists: Set of current tourist IDs from classification
            created_visitor_ids: Set of visitor IDs with created_at >= start_date
            updated_visitor_ids: Set of visitor IDs with updated_at >= start_date
            all_db_visitor_ids: Set of all visitor IDs currently in DB

        Returns:
            dict: Dictionary with newUniqueVisitors, newResidentUniqueVisitors, newTouristUniqueVisitors
        """
        # New unique visitors = all visitors created after start_date
        new_unique_visitors_created = created_visitor_ids
        new_unique_visitors_not_in_db = created_visitor_ids - all_db_visitor_ids
        new_unique_visitors = new_unique_visitors_created | new_unique_visitors_not_in_db
        new_unique_visitor_count = len(new_unique_visitors)

        # New resident unique visitors = residents that were updated after start_date OR not in DB
        new_resident_updated = current_residents & updated_visitor_ids
        new_resident_not_in_db = current_residents - all_db_visitor_ids
        new_residents_unique = new_resident_updated | new_resident_not_in_db
        new_resident_unique_visitor_count = len(new_residents_unique)

        # New tourist unique visitors = tourists that were updated after start_date OR not in DB
        new_tourist_updated = current_tourists & updated_visitor_ids
        new_tourist_not_in_db = current_tourists - all_db_visitor_ids
        new_tourist_unique_visitors = new_tourist_updated | new_tourist_not_in_db
        new_tourist_unique_visitor_count = len(new_tourist_unique_visitors)

        return {
            'newUniqueVisitors': new_unique_visitor_count,
            'newResidentUniqueVisitors': new_resident_unique_visitor_count,
            'newTouristUniqueVisitors': new_tourist_unique_visitor_count
        }

    def __compute_new_unique_visitors(self):
        """
        Compute new unique visitor counts based on created_at timestamp.
        A visitor is "new unique" if their DB row was created after start_date.

        Returns:
            dict: Dictionary with newUniqueVisitors, newResidentUniqueVisitors, newTouristUniqueVisitors
        """
        # Build previous visitor types dictionary
        previous_visitor_types = {visitor.visitor_id: visitor.visitor_type for visitor in self.previous_visitors}

        # Classify visitors if not already done
        if not hasattr(self, 'classified_visitors') or self.classified_visitors is None:
            self.classified_visitors = classify_visitors(self.df_raw, previous_visitor_types)

        if self.classified_visitors is None or self.classified_visitors.empty:
            return {'newUniqueVisitors': 0, 'newResidentUniqueVisitors': 0, 'newTouristUniqueVisitors': 0}

        current_residents, current_tourists = self.__get_current_visitor_sets()
        created_visitor_ids = self.__get_created_visitor_ids()
        updated_visitor_ids = self.__get_updated_visitor_ids()
        all_db_visitor_ids = {visitor.visitor_id for visitor in self.previous_visitors}

        result = self.__calculate_new_unique_visitor_counts(
            current_residents, current_tourists,
            created_visitor_ids, updated_visitor_ids, all_db_visitor_ids
        )

        return result

    def transform(self):
        
        self.df_raw['timeinstant'] = pd.to_datetime(self.df_raw['timeinstant'], errors='coerce')
        self.df_raw = self.df_raw.dropna(subset=['timeinstant'])

        if self.df_raw.empty:
            logging.warning("No data to work with.")
            return {
                "result": pd.DataFrame(),
                "new_visitor_counts": self.new_visitor_counts
            }

        time_bins = self._generate_relative_time_bins()

        # Compute new visitor counts only for non-Daily aggregation modes
        if self.aggregation_mode != 'Daily':
            new_unique_counts = self.__compute_new_unique_visitors()
            self.new_visitor_counts.update(new_unique_counts)

        if time_bins:
            self.df_raw['period_bin'] = pd.cut(
                self.df_raw['timeinstant'],
                bins=time_bins,
                right=True,
                include_lowest=True,
                precision=0
            )

            self.result = self.df_raw.groupby(['entityid', 'period_bin'])['visitorid'].nunique().reset_index()

            self.result['period_date'] = self.result['period_bin'].apply(lambda interval: interval.right.to_pydatetime() if pd.notna(interval) else None)
            
            self.result = self.result.dropna(subset=['period_date'])
            self.result = self.result.drop(columns=['period_bin'])
            
            self.result = self.result.rename(columns={'visitorid': 'unique_visitors'})

        else:
            self.result = self.df_raw.groupby('entityid')['visitorid'].nunique().reset_index()
            self.result = self.result.rename(columns={'visitorid': 'unique_visitors'})
            
            self.result['period_date'] = self.end_date

        return {
            "result": self.result,
            "new_visitor_counts": self.new_visitor_counts
        }