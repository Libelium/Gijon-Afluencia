"""
This module contains the constants used in the Orion-LD TimeScaleDB data source.
"""

# all tenant databases are like "orion_<tenant>"
DATABASE_PREFIX = "orion"

# all attribute ids are like "https://uri.etsi.org/ngsi-ld/default-context/<attribute_name>"
ATTRIBUTE_PREFIX = "https://uri.etsi.org/ngsi-ld/default-context/"

# all timeseries are stored in table "attributes"
TABLE_NAME = "attributes"