from fastapi import APIRouter

from app.api.v1.routes import notification_router
from app.api.v1.routes import iota_command_proxy
from app.api.v1.routes import ote_data_router


api_router = APIRouter()

api_router.include_router(
    notification_router.router, prefix="/notify", tags=["Notifications"]
)
api_router.include_router(
    iota_command_proxy.router, prefix="/command-proxy", tags=["Commands"]
)

api_router.include_router(
    ote_data_router.router, prefix="/ote", tags=["OTE LIDAR"]
)
