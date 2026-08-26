from datetime import datetime

from pydantic import BaseModel


class TaskRequest(BaseModel):
    task: str
    params: dict
