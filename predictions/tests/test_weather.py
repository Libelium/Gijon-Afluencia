import os
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from crowd_predictions.weather import (
    fetch_historical_weather, fetch_forecast_weather, update_weather_cache,
    load_weather_cache, save_weather_cache, weather_for, weather_cache_key,
    coordinates_for_current_tenant,
)


def _mock_response(hourly: dict):
    resp = MagicMock()
    resp.json.return_value = {"hourly": hourly}
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_historical_weather_never_hits_the_real_network():
    """requests.get is replaced by a Mock - not a single real call to Open-Meteo."""
    hourly = {
        "time": ["2026-06-01T10:00", "2026-06-01T11:00"],
        "precipitation": [0.0, 2.4],
        "temperature_2m": [21.0, 20.5],
    }
    with patch("crowd_predictions.weather.requests.get", return_value=_mock_response(hourly)) as mock_get:
        points = fetch_historical_weather(date(2026, 6, 1), date(2026, 6, 1), lat=43.5, lon=-5.66)

    assert mock_get.call_count == 1
    called_url = mock_get.call_args[0][0]
    assert called_url == "https://archive-api.open-meteo.com/v1/archive"
    assert points == [
        {"timestamp": datetime(2026, 6, 1, 10), "precip_mm": 0.0, "temp_c": 21.0},
        {"timestamp": datetime(2026, 6, 1, 11), "precip_mm": 2.4, "temp_c": 20.5},
    ]


def test_fetch_forecast_weather_hits_the_forecast_endpoint_with_forecast_days_and_past_days():
    """past_days=7 (default) is what closes ERA5's own lag - see
    update_weather_cache's null-handling tests below."""
    hourly = {"time": ["2026-07-01T00:00"], "precipitation": [0.0], "temperature_2m": [18.0]}
    with patch("crowd_predictions.weather.requests.get", return_value=_mock_response(hourly)) as mock_get:
        fetch_forecast_weather(lat=43.5, lon=-5.66, forecast_days=16)

    called_url = mock_get.call_args[0][0]
    called_params = mock_get.call_args[1]["params"]
    assert called_url == "https://api.open-meteo.com/v1/forecast"
    assert called_params["forecast_days"] == 16
    assert called_params["past_days"] == 7


def test_cache_key_is_segregated_by_tenant_and_scope():
    with patch.dict(os.environ, {"FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "tenant_a"}):
        assert weather_cache_key() == "weather-cache/libelium/tenant_a/weather_cache.json"


# --- Per-tenant coordinates (WEATHER_TARGETS) - a single WEATHER_LAT/LON would
# apply one city's rain to every tenant in a multi-tenant deployment ---

def test_coordinates_for_current_tenant_falls_back_to_weather_lat_lon_when_targets_is_empty():
    """WEATHER_TARGETS unset -> unchanged single-tenant behaviour."""
    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_a", "WEATHER_LAT": "43.54", "WEATHER_LON": "-5.66"}):
        assert coordinates_for_current_tenant() == (43.54, -5.66)


def test_coordinates_for_current_tenant_picks_the_active_tenants_entry():
    targets = "tenant_a:43.54:-5.66,tenant_b:41.65:-0.88"
    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_b", "WEATHER_TARGETS": targets}):
        assert coordinates_for_current_tenant() == (41.65, -0.88)


def test_coordinates_for_current_tenant_two_tenants_get_two_different_cities():
    """The actual multi-tenant scenario: NOT just "does not crash" - each
    tenant's own coordinates, not the first one's leaking into the second."""
    targets = "tenant_a:43.54:-5.66,tenant_b:41.65:-0.88"
    with patch.dict(os.environ, {"WEATHER_TARGETS": targets}):
        with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_a"}):
            tenant_a_coords = coordinates_for_current_tenant()
        with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_b"}):
            tenant_b_coords = coordinates_for_current_tenant()

    assert tenant_a_coords == (43.54, -5.66)
    assert tenant_b_coords == (41.65, -0.88)
    assert tenant_a_coords != tenant_b_coords


def test_coordinates_for_current_tenant_returns_none_for_a_tenant_with_no_entry():
    targets = "tenant_a:43.54:-5.66"
    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_b", "WEATHER_TARGETS": targets}):
        assert coordinates_for_current_tenant() is None


def test_coordinates_for_current_tenant_rejects_a_malformed_entry():
    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_a", "WEATHER_TARGETS": "tenant_a:43.54"}):
        try:
            coordinates_for_current_tenant()
            assert False, "should have raised ValueError"
        except ValueError:
            pass


def test_another_tenants_malformed_entry_does_not_break_this_one():
    """The typo is in tenant_b's entry, tenant_a still gets its coordinates. This is
    reached from train_pipeline._metrics() on EVERY run, outside daily_pipeline's
    refresh try/except: parsing the whole string would turn one city's typo into
    a failed training for every other tenant."""
    targets = "tenant_a:43.54:-5.66,tenant_b:41.65"
    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_a", "WEATHER_TARGETS": targets}):
        assert coordinates_for_current_tenant() == (43.54, -5.66)

    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_b", "WEATHER_TARGETS": targets}):
        try:
            coordinates_for_current_tenant()
            assert False, "should have raised ValueError for its OWN entry"
        except ValueError:
            pass


def test_update_weather_cache_uses_the_active_tenants_coordinates(tmp_path):
    """End-to-end: update_weather_cache() itself (not just the coordinate lookup)
    picks the right city for the active tenant."""
    storage = _DictStorage()

    def fake_historical(start_date, end_date, lat, lon):
        assert (lat, lon) == (41.65, -0.88)
        return []

    def fake_forecast(lat, lon, forecast_days=16, past_days=7):
        assert (lat, lon) == (41.65, -0.88)
        return []

    targets = "tenant_a:43.54:-5.66,tenant_b:41.65:-0.88"
    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_b", "WEATHER_TARGETS": targets}), \
         patch("crowd_predictions.weather.fetch_historical_weather", side_effect=fake_historical), \
         patch("crowd_predictions.weather.fetch_forecast_weather", side_effect=fake_forecast):
        update_weather_cache(storage, local_dir=str(tmp_path))


class _DictStorage:
    """The StorageType contract in memory. download_file RAISES when the key is
    missing, which is how load_weather_cache tells "never refreshed" from "has data"."""

    def __init__(self):
        self.files = {}

    def upload_file(self, filename, path):
        with open(path, "rb") as f:
            self.files[filename] = f.read()
        return path

    def download_file(self, filename, path):
        if filename not in self.files:
            raise FileNotFoundError(filename)
        with open(path, "wb") as f:
            f.write(self.files[filename])
        return path

    def delete_file(self, path):
        self.files.pop(path, None)
        return True

    def list_all(self):
        return sorted(self.files)


def test_load_weather_cache_with_nothing_uploaded_yet_returns_empty_dict(tmp_path):
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        assert load_weather_cache(_DictStorage(), local_dir=str(tmp_path)) == {}


def test_load_weather_cache_with_a_truncated_blob_returns_empty_dict_instead_of_raising(tmp_path):
    """The docstring promises "never raises" - json.load on a corrupt/truncated
    file is just as unusable as a download failure, and used to slip past the
    try/except that only wrapped download_file."""
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        storage.files[weather_cache_key()] = b'{"2026-06-01T10:00:00": {"precip_mm": 1.0,'  # cut mid-write
        assert load_weather_cache(storage, local_dir=str(tmp_path)) == {}


def test_cache_round_trips_through_storage(tmp_path):
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        save_weather_cache(storage, {"2026-06-01T10:00:00": {"precip_mm": 3.2, "temp_c": 19.5}},
                           local_dir=str(tmp_path))
        cache = load_weather_cache(storage, local_dir=str(tmp_path))
    assert cache == {"2026-06-01T10:00:00": {"precip_mm": 3.2, "temp_c": 19.5}}


def test_update_weather_cache_merges_new_points_and_prunes_anything_far_older_than_the_fetch_window(tmp_path):
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        # 2020 is far outside any real historical_days_back - the cache must not
        # accumulate every day it has ever seen (see the dedicated pruning tests
        # below for the exact boundary).
        save_weather_cache(storage, {"2020-01-01T00:00:00": {"precip_mm": 9.9, "temp_c": 5.0}},
                           local_dir=str(tmp_path))

        historical_points = [{"timestamp": datetime(2026, 6, 1, 10), "precip_mm": 1.0, "temp_c": 20.0}]
        forecast_points = [{"timestamp": datetime(2026, 7, 1, 0), "precip_mm": 0.0, "temp_c": 18.0}]

        with patch("crowd_predictions.weather.fetch_historical_weather", return_value=historical_points), \
             patch("crowd_predictions.weather.fetch_forecast_weather", return_value=forecast_points), \
             patch.dict(os.environ, {"WEATHER_LAT": "43.5", "WEATHER_LON": "-5.66"}):
            cache = update_weather_cache(storage, forecast_days=16, historical_days_back=400,
                                          local_dir=str(tmp_path))

    assert "2020-01-01T00:00:00" not in cache  # pruned - years outside the fetch window
    assert cache["2026-06-01T10:00:00"] == {"precip_mm": 1.0, "temp_c": 20.0}
    assert cache["2026-07-01T00:00:00"] == {"precip_mm": 0.0, "temp_c": 18.0}
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        assert load_weather_cache(storage, local_dir=str(tmp_path)) == cache  # persisted for real


def test_update_weather_cache_prunes_an_entry_just_past_the_window(tmp_path):
    storage = _DictStorage()
    old_key = (date.today() - timedelta(days=401)).isoformat() + "T00:00:00"
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        save_weather_cache(storage, {old_key: {"precip_mm": 1.0, "temp_c": 5.0}}, local_dir=str(tmp_path))

        with patch("crowd_predictions.weather.fetch_historical_weather", return_value=[]), \
             patch("crowd_predictions.weather.fetch_forecast_weather", return_value=[]), \
             patch.dict(os.environ, {"WEATHER_LAT": "43.5", "WEATHER_LON": "-5.66"}):
            cache = update_weather_cache(storage, historical_days_back=400, local_dir=str(tmp_path))

    assert old_key not in cache


def test_update_weather_cache_keeps_an_entry_right_at_the_edge_of_the_window(tmp_path):
    storage = _DictStorage()
    edge_key = (date.today() - timedelta(days=400)).isoformat() + "T00:00:00"
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        save_weather_cache(storage, {edge_key: {"precip_mm": 1.0, "temp_c": 5.0}}, local_dir=str(tmp_path))

        with patch("crowd_predictions.weather.fetch_historical_weather", return_value=[]), \
             patch("crowd_predictions.weather.fetch_forecast_weather", return_value=[]), \
             patch.dict(os.environ, {"WEATHER_LAT": "43.5", "WEATHER_LON": "-5.66"}):
            cache = update_weather_cache(storage, historical_days_back=400, local_dir=str(tmp_path))

    assert edge_key in cache


def test_update_weather_cache_fills_a_null_historical_reading_with_the_forecast_value(tmp_path):
    """ERA5's own last few days (fetch_historical_weather) often come back with
    precipitation: null - forecast's past_days (fetch_forecast_weather) covers
    exactly that overlap and should win when historical is null."""
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        historical_points = [{"timestamp": datetime(2026, 8, 3, 10), "precip_mm": None, "temp_c": 21.0}]
        forecast_points = [{"timestamp": datetime(2026, 8, 3, 10), "precip_mm": 1.4, "temp_c": 21.2}]

        with patch("crowd_predictions.weather.fetch_historical_weather", return_value=historical_points), \
             patch("crowd_predictions.weather.fetch_forecast_weather", return_value=forecast_points), \
             patch.dict(os.environ, {"WEATHER_LAT": "43.5", "WEATHER_LON": "-5.66"}):
            cache = update_weather_cache(storage, local_dir=str(tmp_path))

    assert cache["2026-08-03T10:00:00"] == {"precip_mm": 1.4, "temp_c": 21.2}


def test_update_weather_cache_never_lets_forecast_overwrite_a_real_historical_reading(tmp_path):
    """The overlap window (past_days) only fills holes - a day ERA5 already
    published cleanly keeps its real measurement, not a forecast guess."""
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        historical_points = [{"timestamp": datetime(2026, 8, 3, 10), "precip_mm": 5.0, "temp_c": 19.0}]
        forecast_points = [{"timestamp": datetime(2026, 8, 3, 10), "precip_mm": 0.0, "temp_c": 21.2}]

        with patch("crowd_predictions.weather.fetch_historical_weather", return_value=historical_points), \
             patch("crowd_predictions.weather.fetch_forecast_weather", return_value=forecast_points), \
             patch.dict(os.environ, {"WEATHER_LAT": "43.5", "WEATHER_LON": "-5.66"}):
            cache = update_weather_cache(storage, local_dir=str(tmp_path))

    assert cache["2026-08-03T10:00:00"] == {"precip_mm": 5.0, "temp_c": 19.0}


def test_update_weather_cache_normalizes_a_null_left_by_both_sources_to_no_rain(tmp_path):
    """Last resort: if even the forecast comes back null for the same hour, the
    cache must never persist a None - that is what would surface as NaN two
    layers up in training_data.py/train_pipeline.py."""
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        historical_points = [{"timestamp": datetime(2026, 8, 3, 10), "precip_mm": None, "temp_c": 21.0}]
        forecast_points = [{"timestamp": datetime(2026, 8, 3, 10), "precip_mm": None, "temp_c": 21.2}]

        with patch("crowd_predictions.weather.fetch_historical_weather", return_value=historical_points), \
             patch("crowd_predictions.weather.fetch_forecast_weather", return_value=forecast_points), \
             patch.dict(os.environ, {"WEATHER_LAT": "43.5", "WEATHER_LON": "-5.66"}):
            cache = update_weather_cache(storage, local_dir=str(tmp_path))

    assert cache["2026-08-03T10:00:00"]["precip_mm"] == 0.0


def test_update_weather_cache_is_a_no_op_without_lat_lon_configured(tmp_path):
    """WEATHER_LAT/WEATHER_LON are optional (see WeatherSettings) - a deployment
    that has not set them yet must not have this crash or fetch garbage coordinates."""
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}, clear=False):
        os.environ.pop("WEATHER_LAT", None)
        os.environ.pop("WEATHER_LON", None)
        with patch("crowd_predictions.weather.fetch_historical_weather") as mock_historical:
            cache = update_weather_cache(storage, local_dir=str(tmp_path))
    mock_historical.assert_not_called()
    assert cache == {}


def test_weather_for_returns_the_cached_point_for_the_exact_hour():
    cache = {"2026-06-01T10:00:00": {"precip_mm": 3.2, "temp_c": 19.5}}
    result = weather_for(datetime(2026, 6, 1, 10, 15), cache)  # same hour, different minute
    assert result == {"precip_mm": 3.2, "temp_c": 19.5}


def test_weather_for_returns_a_copy_not_the_cached_dict_itself():
    """A caller mutating the returned dict must not corrupt the shared in-memory
    cache - every other row read afterwards in the same process goes through
    the same dict."""
    cache = {"2026-06-01T10:00:00": {"precip_mm": 3.2, "temp_c": 19.5}}
    result = weather_for(datetime(2026, 6, 1, 10, 0), cache)
    result["precip_mm"] = 999.0
    assert cache["2026-06-01T10:00:00"]["precip_mm"] == 3.2


def test_weather_for_normalizes_a_tz_aware_timestamp_before_the_lookup():
    """The cache is keyed by naive UTC - a tz-aware timestamp with a non-zero
    offset must still land on the right hour, not silently miss and fall to
    the 0.0 default for the whole dataset."""
    from datetime import timezone as tz
    cache = {"2026-06-01T10:00:00": {"precip_mm": 3.2, "temp_c": 19.5}}
    madrid_noon = datetime(2026, 6, 1, 12, 15, tzinfo=tz(timedelta(hours=2)))  # == 10:15 UTC
    result = weather_for(madrid_noon, cache)
    assert result == {"precip_mm": 3.2, "temp_c": 19.5}


def test_weather_for_a_utc_tz_aware_timestamp_still_matches():
    from datetime import timezone as tz
    cache = {"2026-06-01T10:00:00": {"precip_mm": 3.2, "temp_c": 19.5}}
    result = weather_for(datetime(2026, 6, 1, 10, 15, tzinfo=tz.utc), cache)
    assert result == {"precip_mm": 3.2, "temp_c": 19.5}


def test_weather_for_missing_hour_defaults_to_no_rain_and_unknown_temperature():
    result = weather_for(datetime(2026, 6, 1, 10, 0), {})
    assert result == {"precip_mm": 0.0, "temp_c": None}
