"""
Crowd estimation per zone and device, with 3 cases depending on which sensors
each zone has deployed:

  1. MIXED (LIDAR + Smart Spot): the LIDAR RULES on its own whenever it has a
     reading this window - the crowd figure is always its own, without combining
     it with Smart Spot (not even as a lower bound - see the CHANGE note in
     zone_estimate() below). Smart Spot is reported separately as a diagnostic
     margin (smartspot_delta_pct), never mixed into the figure. On top of that,
     this zone is what lets us LEARN the calibration factor (real people per
     Smart Spot visitor detected), reusable in case 3.
  2. LIDAR ONLY: its count is trusted directly ("identified people") - there are
     no MACs to reconcile, nothing needs calibrating.
  3. SMART SPOT ONLY: the "handle with care" case - there is no local LIDAR to
     validate against, so the average calibration factor learned in the mixed
     zones (case 1) is applied to the raw Smart Spot count. If there is no mixed
     zone with data yet (factor not learned), the raw count is used uncorrected
     and it is flagged as such.

Every estimate comes with a "confidence" level:
  - "measured"              -> comes from a direct presence sensor (cases 1 and 2)
  - "estimated"              -> corrected with a learned calibration factor (case 3)
  - "estimated_uncalibrated" -> case 3 with no mixed zone yet to calibrate with
  - "no_data"                -> case 2 with no LIDAR reading this window and no
                                other sensor in the zone to fall back to - NOT a
                                measured zero, see zone_estimate()

It makes no network or DB calls - it receives the already extracted data
(dict/list in memory). The real extraction lives in etl/crowd/extract.py
(CrowdFlowLidarZone + CrowdFlowObserved from the platform) and plugs in here
without touching this logic.

⚠️ AFORO ≠ AFLUENCIA: `occupancy` here is always the SIMULTANEOUS count - what the
pliego calls "aforo". `lidar_zone_counts` therefore has to carry that same
simultaneous figure per zone (the real datamodel's `totalConcurrentMax`), NEVER
the cumulative one (`totalCount`, "afluencia":
how many distinct people passed through in the window, which can be far larger than
the simultaneous max). There is no afluencia figure anywhere in this module today -
if one is ever added, it has to be its own field, never folded into `occupancy`.
"""

from crowd_predictions.zones_config import ZONES, lidar_coverage_multiplier

MIXED = "mixed"
LIDAR_ONLY = "lidar_only"
SMARTSPOT_ONLY = "smartspot_only"
NONE_DEPLOYED = "none"


def classify_zone_case(zone_id: str) -> str:
    """Which sensors this zone has deployed: mixed / lidar_only / smartspot_only / none."""
    zone = ZONES[zone_id]
    has_lidar = bool(zone.lidar_ids)
    has_smartspot = bool(zone.smartspot_ids)
    if has_lidar and has_smartspot:
        return MIXED
    if has_lidar:
        return LIDAR_ONLY
    if has_smartspot:
        return SMARTSPOT_ONLY
    return NONE_DEPLOYED


def compute_signal_share(smartspot_counts: dict, zone_id: str) -> dict:
    """
    Share of each Smart Spot of a zone over the zone's total signal.

    `smartspot_counts` is {device_id: people counted}, whatever produced it - the
    platform's own aggregate (helpers/smartspot_history.load_smartspot_counts) or
    distinct visitors collapsed from synthetic events (counts_from_events). One
    interface, so this layer does not care where the number came from.
    """
    zone_devices = ZONES[zone_id].smartspot_ids
    if not zone_devices:
        return {}

    signal_counts = {d: smartspot_counts.get(d, 0) for d in zone_devices}
    total_signal = sum(signal_counts.values())

    if total_signal == 0:
        equal_share = 1.0 / len(zone_devices)
        return {d: equal_share for d in zone_devices}

    return {d: count / total_signal for d, count in signal_counts.items()}


def _smartspot_zone_signal(smartspot_counts: dict, zone_id: str) -> int:
    """Raw Smart Spot signal of a zone: the sum of its devices' counts.

    ⚠️ A person walking past two Smart Spots of the same zone is counted TWICE -
    unavoidable without the identities, which the platform does not publish (see
    helpers/smartspot_history.py). Correct it per zone with `coverage_multiplier`
    in zones.json where the sensors really do overlap."""
    zone_devices = ZONES[zone_id].smartspot_ids
    return sum(smartspot_counts.get(d, 0) for d in zone_devices)


def _coverage_adjusted_lidar_count(zone_id: str, raw_lidar_count) -> float | None:
    """
    A LIDAR covers ~180 degrees, not 360 - a raw count typically sees only a PART
    of the zone. Corrects it by multiplying by lidar_coverage_multiplier(zone_id)
    (360 / (no._of_LIDARs_in_the_zone * 180), never below 1.0) before using the
    count in any calculation - see zones_config.py for the detail and the
    assumptions (orientations with no overlap, still not confirmed with real data).
    """
    if raw_lidar_count is None:
        return None
    return raw_lidar_count * lidar_coverage_multiplier(zone_id)


def compute_calibration_factor(lidar_zone_counts: dict, smartspot_counts: dict) -> float | None:
    """
    Average "real people per Smart Spot visitor detected" factor, learned ONLY
    from mixed zones (LIDAR+SmartSpot) with signal present this window. None if
    there is no mixed zone with data yet - case 3 cannot be calibrated without at
    least one real reference point.
    """
    ratios = []
    for zone_id, raw_lidar_count in lidar_zone_counts.items():
        if zone_id not in ZONES or classify_zone_case(zone_id) != MIXED:
            continue
        signal = _smartspot_zone_signal(smartspot_counts, zone_id)
        if signal > 0:
            lidar_count = _coverage_adjusted_lidar_count(zone_id, raw_lidar_count)
            ratios.append(lidar_count / signal)

    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def zone_estimate(zone_id: str, lidar_zone_counts: dict, smartspot_counts: dict,
                   calibration_factor) -> dict:
    """
    Estimates the crowd count of a zone according to its case
    (mixed/lidar_only/smartspot_only), returning {occupancy, confidence, case,
    smartspot_signal, smartspot_delta_pct}.

    `lidar_zone_counts[zone_id]` MUST be a simultaneous count (aforo), not a
    cumulative one (afluencia) - see the module docstring. `occupancy` inherits
    that same meaning.

    In a mixed zone the LIDAR RULES whenever it has a reading this window, and the
    Smart Spot signal is reported SEPARATELY as a diagnostic margin
    (smartspot_delta_pct, positive = Smart Spot over-counts). It is never mixed into
    the occupancy figure: a max() of the two keeps the LARGER, and since Smart Spot
    over-counts as a rule, that means publishing the inflated number instead of the
    measured one.
    """
    case = classify_zone_case(zone_id)
    lidar_count = _coverage_adjusted_lidar_count(zone_id, lidar_zone_counts.get(zone_id))
    smartspot_signal = _smartspot_zone_signal(smartspot_counts, zone_id)
    smartspot_delta_pct = None

    if case == MIXED:
        if lidar_count is not None:
            # The LIDAR rules: it gives the real number (already coverage-corrected).
            # Smart Spot is not mixed into the figure - it is reported as a separate margin.
            occupancy = round(lidar_count)
            confidence = "measured"
            if occupancy > 0:
                smartspot_delta_pct = round((smartspot_signal - occupancy) / occupancy * 100, 1)
        else:
            # LIDAR with no reading this window (not "0 people", but "no data") -
            # fall back to Smart Spot, same as the smartspot_only case.
            if calibration_factor is not None:
                occupancy = round(smartspot_signal * calibration_factor)
                confidence = "estimated"
            else:
                occupancy = smartspot_signal
                confidence = "estimated_uncalibrated"

    elif case == LIDAR_ONLY:
        if lidar_count is not None:
            # People identified directly by LIDAR (already coverage-corrected) -
            # there are no MACs to reconcile.
            occupancy = round(lidar_count)
            confidence = "measured"
        else:
            # No LIDAR reading this window, and - unlike the MIXED case - no Smart
            # Spot in this zone to fall back to. `round(lidar_count or 0)` used to
            # publish this as a measured zero, indistinguishable from a genuinely
            # empty zone; None + "no_data" says "we don't know" instead of lying.
            occupancy = None
            confidence = "no_data"

    elif case == SMARTSPOT_ONLY:
        # Handle with care: with no local LIDAR, correct with the factor learned in mixed zones.
        if calibration_factor is not None:
            occupancy = round(smartspot_signal * calibration_factor)
            confidence = "estimated"
        else:
            occupancy = smartspot_signal
            confidence = "estimated_uncalibrated"

    else:
        occupancy = 0
        confidence = "unknown"

    return {
        "occupancy": occupancy,
        "confidence": confidence,
        "case": case,
        "smartspot_signal": smartspot_signal,
        "smartspot_delta_pct": smartspot_delta_pct,
    }


def estimate_zone_totals(lidar_zone_counts: dict, smartspot_counts: dict) -> dict:
    """
    Crowd totals per zone ready for CrowdFlowZone (occupancy/confidence), for every zone with any device deployed AND something to report
    this window - a LIDAR-only zone with no reading and nothing to fall back to
    (confidence="no_data") is skipped entirely rather than publishing a occupancy=0
    that would look like a genuinely empty zone.
    """
    calibration_factor = compute_calibration_factor(lidar_zone_counts, smartspot_counts)

    totals = {}
    for zone_id, zone in ZONES.items():
        if classify_zone_case(zone_id) == NONE_DEPLOYED:
            continue

        estimate = zone_estimate(zone_id, lidar_zone_counts, smartspot_counts, calibration_factor)
        occupancy = estimate["occupancy"]
        if occupancy is None:
            continue

        totals[zone_id] = {
            "occupancy": occupancy,
            "confidence": estimate["confidence"],
            "case": estimate["case"],
            "smartspot_signal": estimate["smartspot_signal"],
            "smartspot_delta_pct": estimate["smartspot_delta_pct"],
        }
    return totals
