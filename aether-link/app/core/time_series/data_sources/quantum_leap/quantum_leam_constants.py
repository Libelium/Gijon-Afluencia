"""
This module contains the constants used in the Quantum Leap data source
"""

# all schemas are like "mt<tenant>"
SCHEMA_PREFIX = "mt"

# all tables are like "et<entity_type>"
ENTITY_TYPE_PREFIX = "et"

SCOPE_COLUMN = "fiware_servicepath"

# the name of the NGSI atttr that contains the timestamp
# TODO: this might not work for NGSI-LD, so this should be configurable
# for now, we assume that this will only work with NGSI-v2
TIME_ATTR = "time_index"

# the ngsi id attribute (urn)
ID_ATTR = "id"
