import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import hchk
from app.api.v1.routes.api import api_router
from app.core.config.config import settings
from app.core.config.logging import appLogging as log
from app.core.ote import raw_ote_archiver

root_router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    raw_ote_archiver.start()
    yield
    raw_ote_archiver.stop()


app = FastAPI(
    title="Libelium Fiware Manager",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
)


def get_client_host(request: Request) -> str:
    """Extract client host from request, returning 'unknown' if not available."""
    return request.client.host if request.client else "unknown"


async def format_request_info(request: Request) -> str:
    """Format common request information for logging, including request body."""
    body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            body = body_bytes.decode("utf-8")
    except Exception:
        body = f"<unable to read body: {traceback.format_exc()}> {body_bytes if 'body_bytes' in locals() else ''}"

    return (
        f"Method: {request.method} | "
        f"URL: {request.url} | "
        f"Client: {get_client_host(request)} | "
        f"Body: {body}"
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors (422 Unprocessable Entity) when request body/params are invalid.
    Logs detailed error information including request details and validation errors.
    """
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    request_info = await format_request_info(request)
    log.info(
        f"Validation Error | {request_info} | "
        f"Error: {exc_str} | Details: {exc.errors()}"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions (404, 500, etc.) and log detailed error information.
    This captures all HTTPException raised throughout the application.
    """
    request_info = await format_request_info(request)
    log.info(
        f"HTTP Error {exc.status_code} | {request_info} | " f"Detail: {exc.detail}"
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions and log full traceback.
    This is a catch-all for unhandled exceptions.
    """
    request_info = await format_request_info(request)
    log.error(
        f"Unhandled Exception | {request_info} | "
        f"Exception: {str(exc)} | Traceback: {traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error": str(exc)},
    )


@app.middleware("http")
async def remove_server_header(request: Request, call_next):
    """Remove server banner headers to prevent information disclosure."""
    response = await call_next(request)
    headers_to_remove = ["server", "x-powered-by"]
    for header in headers_to_remove:
        if header in response.headers:
            del response.headers[header]
    return response


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    """Log request processing time and status for each HTTP request."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    log_func = log.info if response.status_code < 400 else log.warning
    log_func(
        f"Request: {request.method} {request.url} | "
        f"Duration: {duration:.4f}s | Status: {response.status_code}"
    )
    return response


app.include_router(hchk.router, prefix="")
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(root_router)
