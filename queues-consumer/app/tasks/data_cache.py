from schemas.crowd_data_cache_etl_request_schema import (
    CrowdDataCacheETLRequest,
    AllCrowdDataCacheETLRequest,
)
from etls.data_cache.crowd_data_cache_etl.etl import CrowdDataCacheETL
from config.celery import DEFAULT_TASK_ARGS
from config.celery import app as celery_app
from jobs.data_cache.all_data_cache_crowd_jobs import DataCacheCrowdAll

from config.queues import (
    DATA_CACHE_QUEUE_CROWD_ALL_NAME,
    DATA_CACHE_QUEUE_CROWD_NAME,
)
from db.deps import get_db
from db.realtime import get_db_realtime
from config.logging import appLogging as logging
from config.config import settings
from models.crud.crud_etl_executions import (
    get_etl_execution_with_specific_params,
    create_etl_execution,
)


@celery_app.task(
    name="platform.data_cache.crowd_job",
    queue=DATA_CACHE_QUEUE_CROWD_NAME,
    **DEFAULT_TASK_ARGS,
)
def data_cache_crowd_job(self, request: CrowdDataCacheETLRequest) -> None:
    """
    Process an ETL job for crowd data cache
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())

    previous_etl = get_etl_execution_with_specific_params(
        main_db,
        etl_type=DATA_CACHE_QUEUE_CROWD_NAME,
        params=request.model_dump(),
    )

    if not previous_etl or request.force is True:
        if not previous_etl:
            create_etl_execution(
                main_db,
                DATA_CACHE_QUEUE_CROWD_NAME,
                user_id=request.user_id,
                params=request.model_dump(),
            )

        etl = CrowdDataCacheETL(
            request=request, main_db=main_db, realtime_db=realtime_db
        )
        etl.execute_once()

    else:
        logging.info(
            f"Skipping ETL for {DATA_CACHE_QUEUE_CROWD_NAME} with params {request.model_dump()}"
        )


@celery_app.task(
    name="platform.data_cache.crowd_all_job",
    queue=DATA_CACHE_QUEUE_CROWD_ALL_NAME,
    **DEFAULT_TASK_ARGS,
)
def all_data_cache_crowd_job(self, request: AllCrowdDataCacheETLRequest = None) -> None:
    """
    Generate all crowd data cache
    """
    logging.info(f"Processing all crowd data cache jobs")
    main_db = next(get_db())
    req = (
        request
        if request
        else AllCrowdDataCacheETLRequest(
            start_date=None,
            end_date=None,
        )
    )
    job = DataCacheCrowdAll(request=req, db=main_db)
    job.handle()


# Periodic tasks
@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    logging.info("Setting up periodic data cache tasks")
    if not settings.IS_ON_PREMISE:
        sender.add_periodic_task(
            settings.DATA_CACHE_CROWD_PROCESS_INTERVAL,
            all_data_cache_crowd_job.s(),
            name="Process all crowd data cache",
        )
