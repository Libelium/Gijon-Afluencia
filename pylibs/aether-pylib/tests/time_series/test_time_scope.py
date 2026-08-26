import pytest

from aether_pylib.time_series.time_scope import TimeScope
from datetime import datetime


class TestTimeScope:
    @pytest.mark.parametrize(
        ("time_scope_dict"),
        [
            # months
            ({"months": [-1]}),
            ({"months": [12]}),
            # month_days
            ({"month_days": [-1]}),
            ({"month_days": [31]}),
            # week_days
            ({"week_days": [-1]}),
            ({"week_days": [7]}),
            # hours cannot be wrong if the type is correct,
            # time period adjustment
            # year cannot be wrong if the type is correct,
            # month
            ({"extra": [{"month": -1}]}),
            ({"extra": [{"month": 31}]}),
            # month_day
            ({"extra": [{"month_day": -1}]}),
            ({"extra": [{"month_day": 32}]}),
        ],
    )
    def test_invalid_time_scope(self, time_scope_dict: dict):
        """
        Test invalid time scopes, should raise ValueError
        """
        try:
            TimeScope(**time_scope_dict)
            assert False
        except ValueError:
            assert True

    @pytest.mark.parametrize(
        ("date", "time_scope", "is_in_scope"),
        [
            # months
            (datetime(2024, 1, 1, 0, 0), TimeScope(months=[0]), True),
            (datetime(2024, 2, 1, 0, 0), TimeScope(months=[0, 1]), True),
            (datetime(2024, 2, 1, 0, 0), TimeScope(months=[0, 2]), False),
            # month days
            (datetime(2024, 1, 1, 0, 0), TimeScope(month_days=[0]), True),
            (datetime(2024, 1, 2, 0, 0), TimeScope(month_days=[0, 1]), True),
            (datetime(2024, 1, 2, 0, 0), TimeScope(month_days=[0, 2]), False),
            # week days (2024 starts on a Monday)
            (datetime(2024, 1, 1, 0, 0), TimeScope(week_days=[0]), True),
            (datetime(2024, 1, 2, 0, 0), TimeScope(week_days=[0, 1]), True),
            (datetime(2024, 1, 2, 0, 0), TimeScope(week_days=[0, 2]), False),
            # hours
            (
                datetime(2024, 1, 1, 0, 0),
                TimeScope(hours=[["00:00:00", "23:59:59"]]),
                True,
            ),
            (
                datetime(2024, 1, 1, 1, 0),
                TimeScope(hours=[["00:00:00", "01:00:00"]]),
                True,
            ),
            (
                datetime(2024, 1, 1, 1, 0),
                TimeScope(hours=[["15:00:00", "02:00:00"]]),
                True,
            ),
            (
                datetime(2024, 1, 1, 1, 25),
                TimeScope(hours=[["15:00:00", "02:00:00"]]),
                True,
            ),
            (
                datetime(2024, 1, 1, 1, 25),
                TimeScope(hours=[["15:00:00", "01:00:00"]]),
                False,
            ),
            # extra adjustments
            (
                datetime(2024, 1, 1, 0, 0),
                TimeScope(
                    extra=[{"year": 2024, "month": 0, "month_day": 1, "exclude": False}]
                ),
                True,
            ),
            (
                datetime(2024, 1, 2, 0, 0),
                TimeScope(
                    extra=[
                        {"year": 2024, "month": 0, "month_day": 1, "exclude": False},
                        {"year": 2024, "month": 0, "month_day": 2, "exclude": False},
                        {"year": 2024, "month": 0, "month_day": 3, "exclude": True},
                        {"year": 2024, "month": 0, "month_day": 4, "exclude": True},
                    ]
                ),
                True,
            ),
            (
                datetime(2024, 1, 4, 0, 0),
                TimeScope(
                    extra=[
                        {"year": 2024, "month": 0, "month_day": 1, "exclude": False},
                        {"year": 2024, "month": 0, "month_day": 2, "exclude": False},
                        {"year": 2024, "month": 0, "month_day": 3, "exclude": True},
                        {"year": 2024, "month": 0, "month_day": 4, "exclude": True},
                    ]
                ),
                False,
            ),
            (
                datetime(2024, 1, 7, 0, 0),
                TimeScope(
                    extra=[
                        {"year": 2024, "month": 0, "month_day": 1, "exclude": False},
                        {"year": 2024, "month": 0, "month_day": 2, "exclude": False},
                        {"year": 2024, "month": 0, "month_day": 3, "exclude": True},
                        {"year": 2024, "month": 0, "month_day": 4, "exclude": True},
                    ]
                ),
                True,
            ),
            # mixed
            (
                datetime(2024, 1, 1, 0, 0),
                TimeScope(
                    months=[0],
                    month_days=[0],
                    week_days=[0],
                    hours=[["00:00:00", "23:59:59"]],
                ),
                True,
            ),
            (
                datetime(2024, 1, 1, 6, 6),
                TimeScope(
                    months=[0],
                    month_days=[0],
                    week_days=[0],
                    hours=[["00:00:00", "03:59:59"]],
                ),
                False,
            ),
            (
                datetime(2024, 1, 1, 6, 6),
                TimeScope(
                    months=[0],
                    month_days=[0],
                    week_days=[0],
                    hours=[["10:00:00", "07:59:59"]],
                ),
                True,
            ),
            (
                datetime(2024, 1, 1, 6, 6),
                TimeScope(
                    months=[0],
                    month_days=[3],
                    week_days=[0],
                    hours=[["10:00:00", "07:59:59"]],
                ),
                False,
            ),
            (
                datetime(2024, 1, 1, 6, 6),
                TimeScope(
                    months=[0],
                    month_days=[0],
                    week_days=[5],
                    hours=[["10:00:00", "07:59:59"]],
                ),
                False,
            ),
            (
                datetime(2024, 1, 1, 6, 6),
                TimeScope(
                    months=[0],
                    month_days=[0],
                    week_days=[0],
                    hours=[["10:00:00", "07:59:59"]],
                    extra=[
                        {"year": 2024, "month": 0, "month_day": 0, "exclude": True}
                    ],
                ),
                False,
            ),
            (
                datetime(2024, 1, 1, 6, 6),
                TimeScope(
                    months=[0],
                    month_days=[5],
                    week_days=[0],
                    hours=[["10:00:00", "07:59:59"]],
                    extra=[
                        {"year": 2024, "month": 0, "month_day": 0, "exclude": False}
                    ],
                ),
                True,
            ),
            (
                datetime(2024, 1, 1, 6, 30),
                TimeScope(
                    months=[],
                    month_days=[],
                    week_days=[0],
                    hours=[["07:00:00", "07:59:59"]],
                    timezone="Europe/Madrid",
                ),
                True,
            ),
            (
                datetime(2024, 1, 1, 6, 30),
                TimeScope(
                    months=[],
                    month_days=[],
                    week_days=[0],
                    hours=[["07:00:00", "07:59:59"]],
                    timezone="America/New_York",
                ),
                False,
            )
        ],
    )
    def test_generic(self, date: datetime, time_scope: TimeScope, is_in_scope: bool):
        """
        Generic test for time scopes, pretty straightforward
        """
        assert time_scope.in_scope(date) == is_in_scope
