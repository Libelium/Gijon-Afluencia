from typing import Any
from pydantic import BaseModel
from datetime import datetime

class NgsiCmdInfo(BaseModel):
    entity_urn : str
    entity_tenant: str
    entity_scope: str
    entity_type : str
    cmd_name : str
    cmd_info: Any
    cmd_status: Any
    ts_cmd_info: datetime
    ts_cmd_status: datetime