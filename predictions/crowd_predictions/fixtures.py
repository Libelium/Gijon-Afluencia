"""
Generator of synthetic data (fictitious Smart Spot + LIDAR) to test the algorithm
locally, with no real sensors and no infrastructure.

This is not "step 2" of the plan (tests in pre with fictitious sensors via
Airflow/Orion-LD), it is only so that the logic of this step 1 can be run and
debugged on the machine itself.
"""

import random
from datetime import datetime, timedelta

from crowd_predictions.zones_config import ZONES

RESIDENT_VISITOR_IDS = [f"resident_{i}" for i in range(5)]
TOURIST_VISITOR_IDS = [f"tourist_{i}" for i in range(30)]


def generate_events(days: int = 10, seed: int = 42) -> list:
    """
    Generates raw Smart Spot events for `days` full days.

    - Residents: they show up almost every day, always in the morning, on 1-2
      devices of a fixed zone (it simulates somebody who lives/works nearby).
    - Tourists: they show up just once in the whole period, strolling through 3-5
      zones in a row on the same afternoon (it simulates a short visit with a
      route).

    Returns a list of dicts {visitorid, device_id, timestamp}.
    """
    rng = random.Random(seed)
    events = []
    # Only zones with a Smart Spot: a resident needs a device that detects them.
    smartspot_zones = [z for z in ZONES.values() if z.smartspot_ids]
    start_date = datetime(2026, 6, 1)

    for day in range(days):
        date = start_date + timedelta(days=day)

        for resident_idx, visitorid in enumerate(RESIDENT_VISITOR_IDS):
            if rng.random() < 0.9:  # misses the odd day, realistic behaviour
                # Fixed index per resident, NOT hash(str) (not deterministic across
                # runs because of PYTHONHASHSEED - an error already seen in the
                # reference repo).
                zone = smartspot_zones[resident_idx % len(smartspot_zones)]
                device_id = zone.smartspot_ids[0]
                hour = rng.randint(8, 10)
                minute = rng.randint(0, 59)
                events.append({
                    "visitorid": visitorid,
                    "device_id": device_id,
                    "timestamp": date.replace(hour=hour, minute=minute),
                })

        # One new tourist per day, walking through several zones in a row
        tourist_id = TOURIST_VISITOR_IDS[day % len(TOURIST_VISITOR_IDS)]
        n_stops = rng.randint(3, 5)
        route_zones = rng.sample(smartspot_zones, k=min(n_stops, len(smartspot_zones)))
        hour = rng.randint(11, 16)
        minute = rng.randint(0, 30)
        for zone in route_zones:
            events.append({
                "visitorid": tourist_id,
                "device_id": zone.smartspot_ids[0],
                "timestamp": date.replace(hour=hour, minute=minute),
            })
            minute += rng.randint(15, 40)
            if minute >= 60:
                hour += minute // 60
                minute %= 60

    return events


def generate_lidar_zone_counts(events: list, noise: float = 0.15, seed: int = 42) -> dict:
    """
    Simulates the LIDAR count (ground truth) per zone for the LAST hour present in
    `events`, from the no. of unique Smart Spot visitorid of that zone.

    The LIDAR counts PHYSICAL BODIES; Smart Spot counts DEVICES (MAC). A real
    person usually carries several gadgets with their own radio at the same time
    (phone, watch, headphones, tablet) which Smart Spot detects as different
    visitorid if they are not linked - that is why the Smart Spot signal (no. of
    unique visitorid) typically OVER-counts the real people, and the LIDAR
    (people, not gadgets) comes out lower, not the other way round.
    DEVICES_PER_PERSON_RANGE approximates how many detectable gadgets a person
    carries on average.
    """
    if not events:
        return {}

    rng = random.Random(seed)
    last_ts = max(e["timestamp"] for e in events)
    last_hour_events = [e for e in events if e["timestamp"].replace(minute=0, second=0) == last_ts.replace(minute=0, second=0)]

    device_zone = {}
    for zone in ZONES.values():
        for device_id in zone.smartspot_ids:
            device_zone[device_id] = zone.zone_id

    counts_by_zone = {}
    for event in last_hour_events:
        zone_id = device_zone.get(event["device_id"])
        if zone_id:
            counts_by_zone.setdefault(zone_id, set()).add(event["visitorid"])

    DEVICES_PER_PERSON_RANGE = (1.6, 2.4)  # phone + watch/headphones/tablet, typical
    return {
        zone_id: max(0, round(len(visitors) / rng.uniform(*DEVICES_PER_PERSON_RANGE) * rng.uniform(1 - noise, 1 + noise)))
        for zone_id, visitors in counts_by_zone.items()
    }
