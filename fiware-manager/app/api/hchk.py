from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/hchk", status_code=200)
def test():
    """
    Returns 200 (necessary for AWS docker)
    """
    return JSONResponse(status_code=200, content={"status": "OK"})
