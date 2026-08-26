from crowd_predictions.lidar_estimation import (
    classify_zone_case,
    compute_signal_share,
    compute_calibration_factor,
    zone_estimate,
    estimate_zone_totals,
    MIXED,
    LIDAR_ONLY,
    SMARTSPOT_ONLY,
)
from crowd_predictions.helpers.smartspot_history import counts_from_events
from crowd_predictions.zones_config import lidar_coverage_multiplier, ZONES

# The fusion takes {device_id: count}. These tests describe their input as raw
# detections because that is what reads clearly ("two visitors on SS5"), and
# collapse them the same way the synthetic path does.
_c = counts_from_events


def test_classify_zone_case():
    assert classify_zone_case("Z01") == MIXED           # has SS5 + L1..L6
    assert classify_zone_case("Z14") == LIDAR_ONLY       # only L24/L25
    assert classify_zone_case("Z13") == SMARTSPOT_ONLY   # only SS1


def test_signal_share_sums_to_one():
    events = [
        {"device_id": "SS5", "visitorid": "v1", "timestamp": "t"},
        {"device_id": "SS5", "visitorid": "v2", "timestamp": "t"},
    ]
    share = compute_signal_share(_c(events), "Z01")
    assert abs(sum(share.values()) - 1.0) < 1e-9
    assert share["SS5"] == 1.0


def test_mixed_zone_lidar_always_wins_no_safety_floor():
    """Case 1 (2026-07-16): the LIDAR rules whenever it has a reading - there is NO
    longer a Smart Spot safety floor. Smart Spot is reported separately as a margin."""
    events = [{"device_id": "SS5", "visitorid": "v1", "timestamp": "t"}]  # signal=1
    estimate = zone_estimate("Z01", {"Z01": 20}, _c(events), calibration_factor=None)
    assert estimate["occupancy"] == 20
    assert estimate["confidence"] == "measured"
    assert estimate["case"] == MIXED
    assert estimate["smartspot_signal"] == 1
    assert estimate["smartspot_delta_pct"] == -95.0  # (1-20)/20*100

    # If Smart Spot shows MORE people than the LIDAR, it is NO longer raised to that
    # figure - the LIDAR still rules (unlike the previous behaviour).
    many_events = [{"device_id": "SS5", "visitorid": f"v{i}", "timestamp": "t"} for i in range(50)]
    estimate2 = zone_estimate("Z01", {"Z01": 10}, _c(many_events), calibration_factor=None)
    assert estimate2["occupancy"] == 10
    assert estimate2["smartspot_signal"] == 50
    assert estimate2["smartspot_delta_pct"] == 400.0  # (50-10)/10*100, over-count detected


def test_mixed_zone_falls_back_to_smartspot_when_lidar_has_no_reading():
    """If the LIDAR has no reading this window (None, not 0), it falls back to the
    same fallback as smartspot_only - a LIDAR 0 is not made up."""
    events = [{"device_id": "SS5", "visitorid": f"v{i}", "timestamp": "t"} for i in range(3)]
    estimate = zone_estimate("Z01", {}, _c(events), calibration_factor=2.0)
    assert estimate["occupancy"] == 6  # 3 * factor 2.0
    assert estimate["confidence"] == "estimated"
    assert estimate["case"] == MIXED
    assert estimate["smartspot_delta_pct"] is None  # with no LIDAR reading, no margin to compute


def test_lidar_only_zone_trusts_lidar_directly():
    """Case 2: people identified by LIDAR, with no need for Smart Spot."""
    estimate = zone_estimate("Z14", {"Z14": 12}, {}, calibration_factor=None)
    assert estimate["occupancy"] == 12
    assert estimate["confidence"] == "measured"
    assert estimate["case"] == LIDAR_ONLY
    assert estimate["smartspot_signal"] == 0
    assert estimate["smartspot_delta_pct"] is None


def test_lidar_only_zone_with_no_reading_is_no_data_not_a_measured_zero():
    """Unlike MIXED, a lidar_only zone has no Smart Spot to fall back to - a
    missing LIDAR reading must not become a fabricated occupancy=0."""
    estimate = zone_estimate("Z14", {}, {}, calibration_factor=None)
    assert estimate["occupancy"] is None
    assert estimate["confidence"] == "no_data"
    assert estimate["case"] == LIDAR_ONLY


def test_smartspot_only_zone_applies_learned_calibration_factor():
    """Case 3: with no local LIDAR, it is corrected with the average factor of the mixed zones."""
    events = [{"device_id": "SS1", "visitorid": f"v{i}", "timestamp": "t"} for i in range(10)]
    estimate = zone_estimate("Z13", {}, _c(events), calibration_factor=2.5)
    assert estimate["occupancy"] == 25
    assert estimate["confidence"] == "estimated"
    assert estimate["case"] == SMARTSPOT_ONLY


def test_smartspot_only_zone_without_calibration_data_uses_raw_signal():
    """With no mixed zone with data yet, it cannot be calibrated - it is flagged explicitly."""
    events = [{"device_id": "SS1", "visitorid": "v1", "timestamp": "t"}]
    estimate = zone_estimate("Z13", {}, _c(events), calibration_factor=None)
    assert estimate["occupancy"] == 1
    assert estimate["confidence"] == "estimated_uncalibrated"
    assert estimate["case"] == SMARTSPOT_ONLY


def test_calibration_factor_learned_only_from_mixed_zones():
    events = [{"device_id": "SS5", "visitorid": f"v{i}", "timestamp": "t"} for i in range(4)]
    # Z01 is mixed: LIDAR=20, signal=4 -> ratio=5.0
    factor = compute_calibration_factor({"Z01": 20}, _c(events))
    assert factor == 5.0


def test_calibration_factor_none_without_mixed_zone_data():
    factor = compute_calibration_factor({}, {})
    assert factor is None


def test_zone_totals_include_confidence_and_case():
    totals = estimate_zone_totals({"Z01": 150}, _c([{"device_id": "SS5", "visitorid": "v1", "timestamp": "t"}]))
    assert totals["Z01"]["occupancy"] == 150
    assert totals["Z01"]["confidence"] == "measured"
    assert totals["Z01"]["case"] == MIXED
    # Z14 (LIDAR only) has no LIDAR count this window and nothing to fall back to -
    # "no_data", not a fabricated zero, so it is absent from totals entirely.
    assert "Z14" not in totals


def test_zone_totals_skips_lidar_only_zones_with_no_data():
    """Direct check of the skip, isolated from whatever else Z01/other zones do."""
    totals = estimate_zone_totals({}, {})
    assert "Z14" not in totals


def test_lidar_coverage_multiplier_formula():
    """A sector LIDAR -> x1/coverage, it only sees part of the zone. 2+ well spread ->
    x1, capped at 100% coverage, it is not over-corrected for having extra sensors."""
    zone = ZONES["Z03"]
    assert len(zone.lidar_ids) == 1
    zone.fov_by_lidar[zone.lidar_ids[0]] = 180.0   # declared sector, half the circle
    assert lidar_coverage_multiplier("Z03") == 2.0

    assert len(ZONES["Z14"].lidar_ids) == 2
    assert lidar_coverage_multiplier("Z14") == 1.0

    assert len(ZONES["Z01"].lidar_ids) == 6
    assert lidar_coverage_multiplier("Z01") == 1.0

    assert len(ZONES["Z13"].lidar_ids) == 0
    assert lidar_coverage_multiplier("Z13") == 1.0  # with no LIDAR, it does not apply


def test_lidar_coverage_configurable_per_sensor_fov():
    """Each LIDAR declares its own field of view in zones.json: a well mounted
    sensor says so and the correction drops or disappears by itself, without
    touching the formula."""
    zone = ZONES["Z03"]
    assert len(zone.lidar_ids) == 1
    lidar_id = zone.lidar_ids[0]

    # Undeclared: the default is the installed model, omnidirectional -> nothing to
    # correct. The default must never inflate the published headline figure.
    assert lidar_coverage_multiplier("Z03") == 1.0

    zone.fov_by_lidar[lidar_id] = 300.0
    assert lidar_coverage_multiplier("Z03") == 360 / 300.0

    zone.fov_by_lidar[lidar_id] = 360.0     # omnidirectional: nothing to correct
    assert lidar_coverage_multiplier("Z03") == 1.0


def test_an_undeclared_fov_does_not_inflate_the_published_count():
    """It used to assume half a circle and DOUBLE the zone's occupancy, published with
    confidence="measured" and no warning. The installed sensors are omnidirectional."""
    zone = ZONES["Z03"]
    assert zone.fov_by_lidar == {}
    assert lidar_coverage_multiplier("Z03") == 1.0
    estimate = zone_estimate("Z03", {"Z03": 10},
                             _c([{"device_id": "SS4", "visitorid": "v1", "timestamp": "t"}]),
                             calibration_factor=None)
    assert estimate["occupancy"] == 10


def test_a_measured_coverage_multiplier_beats_the_fov_formula():
    """`coverage_multiplier` on the zone is the escape hatch for when the real
    combined coverage is not the simple sum of the FOVs."""
    zone = ZONES["Z03"]
    zone.fov_by_lidar[zone.lidar_ids[0]] = 90.0   # would give x4
    zone.coverage_multiplier = 1.5
    assert lidar_coverage_multiplier("Z03") == 1.5


def test_mixed_zone_with_single_lidar_applies_coverage_correction():
    """
    The case that motivated the adjustment: a zone with a single 180 degree LIDAR - a
    raw count of 10 actually represents ~20 people across the whole zone (only half
    the square was seen), and that 20 is the one that must be used, not the raw 10.
    """
    ZONES["Z03"].fov_by_lidar[ZONES["Z03"].lidar_ids[0]] = 180.0
    events = [{"device_id": "SS4", "visitorid": "v1", "timestamp": "t"}]  # signal=1
    estimate = zone_estimate("Z03", {"Z03": 10}, _c(events), calibration_factor=None)
    assert estimate["occupancy"] == 20  # 10 * 2.0, not 10


def test_calibration_factor_uses_coverage_corrected_lidar_count():
    """The calibration factor must also be learned over the count ALREADY corrected
    by coverage, not over the raw one (same case, Z03 = 1 sector LIDAR)."""
    ZONES["Z03"].fov_by_lidar[ZONES["Z03"].lidar_ids[0]] = 180.0
    events = [{"device_id": "SS4", "visitorid": f"v{i}", "timestamp": "t"} for i in range(4)]
    # Z03 (1 LIDAR at 180deg): raw=10 -> corrected=20; signal=4 -> 20/4=5.0 (not 2.5)
    factor = compute_calibration_factor({"Z03": 10}, _c(events))
    assert factor == 5.0
