from enum import Enum

class ResourceType(str, Enum):
    ENTITY_GROUPS = "entity_groups"
    DEVICES = "devices"
    ENTITIES = "entities"
    ORGANIZATIONS = "organizations"
    FIWARE_TENANTS = "fiware_tenants"
    USERS = "users"
    OUT_CONNECTORS = "out_connectors"
    REGULATIONS = "regulations"
    DASHBOARDS = "dashboards"
    ALARMS = "alarms"
