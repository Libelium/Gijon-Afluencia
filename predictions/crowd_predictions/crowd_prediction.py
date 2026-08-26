"""
Footfall prediction by day of the week - Phase 5 of
propuesta_implementacion_lidar_smartspot.md, "a first cheap version with no ML:
historical average of the same day of the week (N weeks back)... per zone".

Same as crowd_prediction_etl of the reference repo (ETLS/crowd-flow-etl-main).
It does not depend on real data to work (it operates over ANY already computed
occupancy history, synthetic or real) - it is the infrastructure of the model,
ready for when there is real history from the installed sensors. See README.md
for the reason to build this already even though there is no real data yet.

Model: to predict a Monday, what happened on the N previous Mondays (the same day
of the week) is averaged, hour by hour - it is not a global average, it is per
time slot, so that a CURVE of the day can be predicted, not just a total number.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from crowd_predictions.config import settings


def _weekday_name(weekday_index: int) -> str:
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return names[weekday_index]


# How many past appearances of the same weekday the baseline averages. One place, so
# the baseline the XGBoost is compared against is the same one documented here.
DEFAULT_N_OCCURRENCES = 8


def _local(ts: datetime, tz: ZoneInfo) -> datetime:
    """Naive-UTC bin -> naive LOCAL time, same conversion training_data does for the
    model. Binned raw, a Sunday 00:30 local lands on Saturday and the baseline gets a
    handicap the model does not have - which would flatter the comparison."""
    aware = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
    return aware.astimezone(tz).replace(tzinfo=None)


def _calendar_timezone() -> ZoneInfo:
    """Resolved once per call and passed down: settings are re-read on every access,
    and this sits inside a per-row loop."""
    return ZoneInfo(settings.calendar().timezone())


def predict_weekday_curve(history: list, zone_id: str, target_date: datetime,
                           n_occurrences: int = DEFAULT_N_OCCURRENCES) -> dict:
    """
    Predicts the hourly curve (0-23h) of crowd count for `target_date` in
    `zone_id`, averaging the last `n_occurrences` appearances of the SAME day of
    the week in `history` that are BEFORE `target_date` (it never looks at data
    from the future relative to the point being predicted).

    history: list of {"zone_id", "timestamp" (datetime), "occupancy"} - the same
    shape that zone_estimate()/estimate_zone_totals() produces when applied
    repeatedly over time (see the example in __main__ or
    generate_synthetic_occupancy_history()).

    Returns {"zone_id", "target_date", "weekday", "n_occurrences_used",
    "hourly_prediction": {hour: mean value or None if there is no history},
    "daily_total_prediction": sum of the hours that have data}.
    """
    target_weekday = target_date.weekday()

    # Every comparison below is on the LOCAL calendar; the stored timestamps are UTC.
    # (local_timestamp, occupancy) pairs rather than copies of the rows: this runs once
    # per zone and per backtested date, and the rest of the row is never read.
    tz = _calendar_timezone()
    target_day = target_date.date()
    same_weekday_past = []
    for h in history:
        if h["zone_id"] != zone_id:
            continue
        local_ts = _local(h["timestamp"], tz)
        if local_ts.weekday() == target_weekday and local_ts.date() < target_day:
            same_weekday_past.append((local_ts, h["occupancy"]))

    # Keeps the last n_occurrences distinct DATES of that day of the week (not
    # the last n_occurrences individual rows - one date can have many rows, one
    # per hour).
    distinct_dates = sorted({ts.date() for ts, _ in same_weekday_past}, reverse=True)
    dates_used = set(distinct_dates[:n_occurrences])

    by_hour = defaultdict(list)
    for local_ts, occupancy in same_weekday_past:
        if local_ts.date() in dates_used:
            by_hour[local_ts.hour].append(occupancy)

    hourly_prediction = {
        hour: round(sum(values) / len(values), 1) if values else None
        for hour, values in ((h, by_hour.get(h, [])) for h in range(24))
    }

    known_hours = [v for v in hourly_prediction.values() if v is not None]

    return {
        "zone_id": zone_id,
        "target_date": target_date.date().isoformat(),
        "weekday": _weekday_name(target_weekday),
        "n_occurrences_used": len(dates_used),
        "hourly_prediction": hourly_prediction,
        "daily_total_prediction": round(sum(known_hours), 1) if known_hours else None,
    }


def backtest_weekday_prediction(history: list, zone_id: str, holdout_date: datetime,
                                  n_occurrences: int = DEFAULT_N_OCCURRENCES) -> dict:
    """
    Validates the model: predicts `holdout_date` using ONLY the history before
    that date (predict_weekday_curve already filters by date < target_date), and
    compares it against the REAL value observed that day in `history` (which IS
    present, since it is synthetic/already known). Gives MAE and MAPE hour by hour.

    This is what makes it possible to say "the model is off by X people on
    average" instead of just "the model works" with no number behind it.
    """
    prediction = predict_weekday_curve(history, zone_id, holdout_date, n_occurrences)

    # Local too, or the actual values would be read from a different set of hours
    # than the prediction was built from.
    tz = _calendar_timezone()
    actual_by_hour = {}
    for h in history:
        if h["zone_id"] != zone_id:
            continue
        local_ts = _local(h["timestamp"], tz)
        if local_ts.date() == holdout_date.date():
            actual_by_hour[local_ts.hour] = h["occupancy"]

    errors = []
    comparison = {}
    for hour in range(24):
        predicted = prediction["hourly_prediction"][hour]
        actual = actual_by_hour.get(hour)
        if predicted is not None and actual is not None:
            errors.append(abs(predicted - actual))
            comparison[hour] = {"predicted": predicted, "actual": actual, "abs_error": round(abs(predicted - actual), 1)}

    mae = round(sum(errors) / len(errors), 2) if errors else None
    actual_values = [c["actual"] for c in comparison.values()]
    mape = (
        round(sum(abs(c["predicted"] - c["actual"]) / c["actual"] for c in comparison.values() if c["actual"] > 0)
               / max(1, sum(1 for c in comparison.values() if c["actual"] > 0)) * 100, 1)
        if actual_values else None
    )

    return {
        "zone_id": zone_id,
        "holdout_date": holdout_date.date().isoformat(),
        "weekday": prediction["weekday"],
        "n_hours_compared": len(comparison),
        "mae": mae,
        "mape_pct": mape,
        "hourly_comparison": comparison,
    }


def generate_synthetic_occupancy_history(zone_id: str, weeks: int = 8, base_amplitude: float = 30.0,
                                           seed: int = 42) -> list:
    """
    ONLY to test/demo the model while there is no real data yet - generates an
    hourly history with a realistic day-of-week pattern (higher weekends,
    midday/evening peak curve) + noise, in the same style as the one used in the
    visual demo of the project (cadence panel). It is not part of the real
    pipeline, it is a fixture of this module.
    """
    import random
    import math

    rng = random.Random(seed)
    start = datetime(2026, 3, 30) # monday
    history = []

    for day in range(weeks * 7):
        date = start + timedelta(days=day)
        weekday = date.weekday()
        weekend_factor = 1.4 if weekday >= 5 else 1.0
        # A small drift per day of the week (e.g. Thursday a bit weaker) so that
        # averaging PER day of the week adds something over a global average.
        weekday_factor = [1.0, 0.95, 0.9, 0.85, 1.1, 1.4, 1.3][weekday]

        for hour in range(24):
            peak = math.exp(-((hour - 13) ** 2) / (2 * 3.5 ** 2)) * 0.6 + math.exp(-((hour - 19) ** 2) / (2 * 3 ** 2)) * 0.75
            base = max(0.03, peak)
            noise = rng.uniform(0.8, 1.2)
            occupancy = round(base_amplitude * base * weekend_factor * weekday_factor * noise)
            history.append({
                "zone_id": zone_id,
                "timestamp": date.replace(hour=hour, minute=0, second=0),
                "occupancy": occupancy,
            })

    return history


if __name__ == "__main__":
    ZONE_ID = "Z01"
    history = generate_synthetic_occupancy_history(ZONE_ID, weeks=8)

    # Predicts the LAST Monday of the history using only the previous Mondays,
    # and compares against the real value (which we do have, since it is
    # synthetic) - this is exactly what is being asked for: "knowing the average
    # of the X previous Mondays, predict how many people there will be next
    # Monday".
    last_date = max(h["timestamp"] for h in history if h["zone_id"] == ZONE_ID)
    mondays = [h["timestamp"] for h in history if h["zone_id"] == ZONE_ID and h["timestamp"].weekday() == 0]
    holdout_monday = max(mondays)

    print(f"Backtest: predicting {holdout_monday.date()} (monday) for zone {ZONE_ID}, "
          f"using only the mondays BEFORE that date.\n")

    result = backtest_weekday_prediction(history, ZONE_ID, holdout_monday, n_occurrences=4)
    print(f"MAE: {result['mae']} people  |  MAPE: {result['mape_pct']}%  "
          f"|  hours compared: {result['n_hours_compared']}\n")

    print(f"{'Hour':<6}{'Predicted':<10}{'Actual':<8}{'Abs. err.':<10}")
    for hour in sorted(result["hourly_comparison"]):
        c = result["hourly_comparison"][hour]
        print(f"{hour:02d}:00 {c['predicted']:<10}{c['actual']:<8}{c['abs_error']:<10}")

    print(f"\nPrediction for ALL days of the week (the next one, over the full history):")
    for weekday_offset in range(7):
        next_date = last_date + timedelta(days=(weekday_offset - last_date.weekday()) % 7 or 7)
        pred = predict_weekday_curve(history, ZONE_ID, next_date, n_occurrences=4)
        print(f"  {pred['weekday']:<10} ({pred['target_date']}): "
              f"total forecast = {pred['daily_total_prediction']} people "
              f"(from {pred['n_occurrences_used']} previous weeks)")
