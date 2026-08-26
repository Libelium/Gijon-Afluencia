import os
from unittest.mock import patch

from crowd_predictions.helpers import smartspot_history


def test_the_lookback_window_covers_the_max_age_accepted():
    """The bug this guards: the two numbers used to be independent and happened to
    match. Raising the limit alone made the freshness check accept readings the query
    never asked for, and the Smart Spot side emptied without an error - which looks
    exactly like a deployment with no Smart Spot."""
    with patch.dict(os.environ, {"LIDAR_ZONE_MAX_AGE_MINUTES": "360"}):
        assert smartspot_history.lookback_hours() == 6
    with patch.dict(os.environ, {"LIDAR_ZONE_MAX_AGE_MINUTES": "200"}):
        assert smartspot_history.lookback_hours() == 4   # rounded up, not down


def test_the_lookback_never_drops_below_the_minimum():
    """A run firing slightly after the hour still has to find the bin it fuses, so a
    small (or disabled, 0 = no freshness check) limit does not shrink the window."""
    for value in ("0", "30", "180"):
        with patch.dict(os.environ, {"LIDAR_ZONE_MAX_AGE_MINUTES": value}):
            assert smartspot_history.lookback_hours() == smartspot_history.MIN_LOOKBACK_HOURS
