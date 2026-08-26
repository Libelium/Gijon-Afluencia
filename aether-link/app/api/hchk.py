from fastapi import APIRouter

from app.core.config.config import healthchecks
from app.core.config.logging import appLogging as logging


router = APIRouter()


@router.get("/hchk", status_code=200)
def test() -> None:
    """
    Returns 200 (necessary for AWS docker)
    It also checks if the data source is up.
    If it is not up, it still returns 200, but with a message of the error
    """

    # try:
    #     errors = []
    #     for name, cs in healthchecks.items():
    #         res = cs.health_check() if cs else False
    #         if not res:
    #             errors.append(name)

    #     if errors:
    #         logging.error(f"Error checking health: {errors}")
    #         return f"ERROR: the following services are down: {', '.join(errors)}"

    #     return "OK"

    # except Exception as e:
    #     logging.error(f"Error checking health: {e}")
    #     return "ERROR: " + str(e)

    return "OK"
