from fastapi import FastAPI, APIRouter, Request

from app.api import hchk
from app.api.v1.routes.api import api_router
from app.core.config.config import settings

root_router = APIRouter()
app = FastAPI(
    title="Context Link",
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
)


@app.middleware("http")
async def remove_server_header(request: Request, call_next):
    """Remove server banner to prevent information disclosure."""
    response = await call_next(request)
    if "Server" in response.headers:
        del response.headers["Server"]
    return response


app.include_router(hchk.router, prefix="")
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(root_router)