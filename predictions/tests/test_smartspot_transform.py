from crowd_predictions.smartspot_transform import transform_smartspot_observed


def test_transform_basic_counts():
    entity = transform_smartspot_observed({
        "device_id": "tenant_a_smartspot_test_1",
        "timestamp_ms": 1783410964588,
        "peopleCountShortInterval": 8,
        "peopleCountMediumInterval": 34,
        "peopleCountLongInterval": 210,
    })
    assert entity["id"] == "urn:ngsi-ld:CrowdFlowObserved:tenant_a_smartspot_test_1"
    assert entity["type"] == "CrowdFlowObserved"
    assert entity["peopleCountShortInterval"] == 8
    assert entity["peopleCountMediumInterval"] == 34
    assert entity["peopleCountLongInterval"] == 210
    assert entity["dateObserved"] == 1783410964


def test_missing_device_id_returns_none():
    assert transform_smartspot_observed({"peopleCountShortInterval": 1}) is None


def test_defaults_counts_to_zero_when_absent():
    entity = transform_smartspot_observed({"device_id": "x", "timestamp_ms": 1000})
    assert entity["peopleCountShortInterval"] == 0
    assert entity["peopleCountMediumInterval"] == 0
    assert entity["peopleCountLongInterval"] == 0


def test_no_visitorid_or_mac_fields_ever_present():
    """CrowdFlowObserved is aggregated - it must never carry CFE-style fields (MAC/visitorId)."""
    entity = transform_smartspot_observed({
        "device_id": "x", "timestamp_ms": 1000, "visitorid": "should_be_ignored",
    })
    assert "visitorid" not in entity
    assert "visitorId" not in entity
    assert "mac" not in entity


def test_known_device_gets_name_and_location_from_zones_config():
    """A device declared in zones.json, with coordinates, gets its name and
    location filled in by itself - the message carries neither."""
    entity = transform_smartspot_observed({
        "device_id": "SS1", "timestamp_ms": 1783410964588,
        "peopleCountShortInterval": 5, "peopleCountMediumInterval": 20, "peopleCountLongInterval": 100,
    })
    assert "Zone 13" in entity["name"]
    assert entity["location"] == {"lat": 10.026, "lon": 20.026}


def test_unknown_device_gets_fallback_name_and_no_location():
    """An unrecognized device: a generic name, without making up coordinates."""
    entity = transform_smartspot_observed({
        "device_id": "tenant_a_smartspot_test_1", "timestamp_ms": 1783410964588,
        "peopleCountShortInterval": 1, "peopleCountMediumInterval": 1, "peopleCountLongInterval": 1,
    })
    assert entity["name"] == "Smart Spot tenant_a_smartspot_test_1"
    assert "location" not in entity


def test_explicit_name_in_msg_overrides_default():
    entity = transform_smartspot_observed({
        "device_id": "SS1", "timestamp_ms": 1000, "name": "Nombre a mano",
    })
    assert entity["name"] == "Nombre a mano"
