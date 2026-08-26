from fastapi import APIRouter
from app.api.v1.routes.time_series import time_series_router
from app.api.v1.routes.context_broker import context_broker_router
from app.api.v1.routes.iot_agent import iot_agent_router

api_router = APIRouter()

api_router.include_router(time_series_router, prefix="/time-series", tags=["time-series"])
api_router.include_router(context_broker_router, prefix="/context-broker", tags=["context-broker"])
api_router.include_router(iot_agent_router, prefix="/iota", tags=["iot-agent"])