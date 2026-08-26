from enum import Enum
from typing import Optional
from pydantic import BaseModel


class DataImportationType(str, Enum):
    """ """

    CSV = "csv"
    XLSX = "xlsx"
    GEOJSON = "geojson"
    KML = "kml"
    JSONLD = "jsonld"


class DataImportationRequest(BaseModel):
    """ """

    user_id: int
    tenant: Optional[str] = None
    scope: Optional[str] = None
    storage_file_path: str
