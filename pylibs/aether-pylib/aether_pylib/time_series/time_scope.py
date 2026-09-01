from datetime import datetime, time, timezone as dt_timezone
from pydantic import BaseModel, field_validator
from typing import List, Optional, Tuple
from enum import Enum
from zoneinfo import ZoneInfo


class TimeScopeAdjustmentType(str, Enum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    NOT_APPLICABLE = "not_applicable"


class TimeScopeAdjustment(BaseModel):
    """
    Time scope adjustment class,
    to add exceptions to the time scope base class.
    """

    year: Optional[int] = None
    # Month is 0 based
    month: Optional[int] = None
    # Month day is 0 based
    month_day: Optional[int] = None
    exclude: bool = True

    @field_validator("month_day", mode="before")
    def validate_month_day(cls, value):
        if value < 0 or value > 30:
            raise ValueError(
                "Invalid month day: {value}. Month day must be between 1 and 31"
            )

        return value

    @field_validator("month", mode="before")
    def validate_month(cls, value):
        if value < 0 or value > 11:
            raise ValueError("Invalid month: {value}. Month must be between 0 and 11")

        return value

    def filter(self, date: datetime) -> TimeScopeAdjustmentType:
        """
        Checks if the given date is included, excluded or not applicable for
        this adjustment.
        """

        in_year: bool = self.year is None or self.year == date.year
        in_month: bool = self.month is None or self.month == date.month - 1
        in_day: bool = self.month_day is None or self.month_day == date.day - 1

        in_scope = in_year and in_month and in_day

        if not in_scope:
            return TimeScopeAdjustmentType.NOT_APPLICABLE

        if self.exclude:
            return TimeScopeAdjustmentType.EXCLUDED

        return TimeScopeAdjustmentType.INCLUDED

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "year": 2020,
                    "month": 0,
                    "month_day": 1,
                }
            ]
        }
    }


class TimeScope(BaseModel):
    """
    Time scope class
    It represents a specific period of time and
    provides the methods to check if a given date
    is inside the scope.
    """

    # month is 0 based
    months: Optional[List[int]] = []
    # month day is 0 based
    month_days: Optional[List[int]] = []
    # week day is 0 based
    week_days: Optional[List[int]] = []
    # hours are hours
    hours: Optional[List[Tuple[time, time]]] = []
    extra: Optional[List[TimeScopeAdjustment]] = []
    # A timezone string (only used in hourly filters)
    timezone: Optional[ZoneInfo] = ZoneInfo("UTC")

    @field_validator("months", mode="before")
    def validate_months(cls, value):
        if not value:
            return None

        for month in value:
            if month < 0 or month > 11:
                raise ValueError(
                    "Invalid month: {month}. Month must be between 1 and 12"
                )

        return value

    @field_validator("month_days", mode="before")
    def validate_month_days(cls, value):
        if not value:
            return None

        for month_day in value:
            if month_day < 0 or month_day > 30:
                raise ValueError(
                    "Invalid month day: {month_day}. Month day must be between 1 and 31"
                )

        return value

    @field_validator("week_days", mode="before")
    def validate_week_days(cls, value):
        if not value:
            return None

        for week_day in value:
            if week_day < 0 or week_day > 6:
                raise ValueError(
                    "Invalid week day: {week_day}. Week day must be between 0 and 6"
                )

        return value

    def in_scope(self, date: datetime) -> bool:
        """
        Checks if the given date is inside the scope.

        A naive `date` is read as UTC. This is not a detail: `datetime.astimezone`
        assumes a naive datetime is in the *system* local time, so before this was
        made explicit the very same call answered differently depending on the
        TZ of the host it ran on. The container runs UTC and CI ran UTC, which is
        why it went unnoticed; on a developer machine set to Europe/Madrid,
        `datetime(2024, 1, 1, 6, 30)` against `hours=[07:00, 07:59:59]` in
        Europe/Madrid returned False instead of True, because 06:30 was taken to
        be 06:30 local rather than 06:30 UTC (FUN-020).

        Every timestamp the platform stores and notifies is UTC, so UTC is the
        right reading for a naive value; an aware `date` is used as given.
        """

        if date.tzinfo is None:
            date = date.replace(tzinfo=dt_timezone.utc)

        # first, check if it it explicitly excluded or included
        if self.extra:
            for adjustment in self.extra:
                extra_status = adjustment.filter(date)
                if extra_status == TimeScopeAdjustmentType.EXCLUDED:
                    return False
                elif extra_status == TimeScopeAdjustmentType.INCLUDED:
                    return True

        # then, check the normal filters
        valid_month = not self.months or date.month - 1 in self.months
        if not valid_month:
            return False

        valid_month_day = not self.month_days or date.day - 1 in self.month_days
        if not valid_month_day:
            return False

        valid_week_day = not self.week_days or date.weekday() in self.week_days
        if not valid_week_day:
            return False

        if not self.hours:
            return True

        # NOTE: months, month_days and week_days above are deliberately evaluated
        # on `date` (UTC), while only the hour window is evaluated in
        # `self.timezone`. That asymmetry is not an oversight here: the SQL side
        # of the same filter does exactly the same thing - see
        # aether-link's query_builder.get_week_day_filtering_condition, which
        # extracts dow/month/day from the raw column, against
        # get_hour_filtering_condition, which applies AT TIME ZONE first. Making
        # this function "more correct" on its own would silently desynchronise it
        # from the query builder, so both sides have to change together.
        timezoned_date = date.astimezone(self.timezone)
        for hour_range in self.hours:
            if hour_range[0] > hour_range[1]:
                if (
                    timezoned_date.time() >= hour_range[0]
                    or timezoned_date.time() <= hour_range[1]
                ):
                    return True

            elif hour_range[0] <= timezoned_date.time() <= hour_range[1]:
                return True

        return False

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "months": [0, 1, 2, 3],
                    "month_days": [],
                    "week_days": [0, 1, 2, 3, 4],
                    "hours": [["12:00:00", "15:00:00"]],
                    "extra": [
                        {
                            "year": 2020,
                            "month": 0,
                            "month_day": 1,
                            "exclude": True,
                        },
                        {
                            "year": 2020,
                            "month": 3,
                            "month_day": 2,
                            "exclude": False,
                        },
                    ],
                }
            ]
        }
    }
