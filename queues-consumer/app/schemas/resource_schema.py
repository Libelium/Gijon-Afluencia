from enum import Enum

class ResourceType(str, Enum):
    ENTITY_GROUPS = "entity_groups"
    DEVICES = "devices"
    ENTITIES = "entities"
    ORGANIZATIONS = "organizations"
    REPORTS = "reports"
    FIWARE_TENANTS = "fiware_tenants"
    USERS = "users"
    DOWNLOADS = "downloads"
    OUT_CONNECTORS = "out_connectors"
    WORKSPACES = "workspaces"
    REGULATIONS = "regulations"
    PROBES = "probes"
    DASHBOARDS = "dashboards"
    ALARMS = "alarms"
