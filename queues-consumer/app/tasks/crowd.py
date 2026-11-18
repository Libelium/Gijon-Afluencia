from schemas.crowd_process_visitors_request_schema import ProcessVisitorsRequest, AllProcessVisitorsRequest
from schemas.crowd_classification_request_schema import CrowdClassificationRequest, AllCrowdClassificationRequest, OneCrowdClassificationRequest
from schemas.crowd_flows_municipality_request_schema import CrowdFlowsMunicipalityRequest, AllCrowdFlowsMunicipalityRequest
from schemas.crowd_unique_visitors_request_schema import CrowdUniqueVisitorsRequest, AllCrowdUniqueVisitorsRequest
from config.celery import DEFAULT_TASK_ARGS
from config.celery import app as celery_app
from etls.crowd.crowd_process_visitors_etl.etl import CrowdProcessVisitorsETL
from etls.crowd.crowd_classification_etl.etl import CrowdClassificationETL
from etls.crowd.crowd_flows_municipality_etl.etl import CrowdFlowsMunicipalityETL
from etls.crowd.crowd_unique_visitors_etl.etl import CrowdUniqueVisitorsETL
from jobs.crowd.all_crowd_classification_jobs import CrowdClassificationAll
from jobs.crowd.all_crowd_unique_visitors_jobs import CrowdUniqueVisitorsAll
from jobs.crowd.all_crowd_flows_municipality_jobs import CrowdFlowsMunicipalityAll
from jobs.crowd.all_crowd_process_vistors_jobs import ProcessVisitorsAll
from jobs.crowd.one_crowd_classification_job import CrowdClassificationOneUser
from config.queues import (
    CROWD_QUEUE_PROCESS_VISITORS_NAME, CROWD_QUEUE_CLASSIFICATION_NAME, CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME, CROWD_QUEUE_PROCESS_VISITORS_ALL_NAME, CROWD_QUEUE_CLASIFICATION_ALL_NAME, CROWD_QUEUE_FLOWS_MUNICIPALITY_ALL_NAME, CROWD_QUEUE_UNIQUE_VISITORS_NAME, CROWD_QUEUE_UNIQUE_VISITORS_ALL_NAME
)
from db.deps import get_db
from db.realtime import get_db_realtime
from config.logging import appLogging as logging
from config.config import settings
import random
from models.crud.crud_etl_executions import (
    find_etl_execution,
    create_etl_execution,
    mark_etl_execution,
    execution_is_successful,
    execution_is_running,
    ETL_STATUS_STARTED,
    ETL_STATUS_SUCCESS,
    ETL_STATUS_FAILED,
)

def etl_retry_countdown(attempt: int) -> float:
    """Capped exponential backoff with up to 10 % jitter."""
    base = min(
        settings.CROWD_ETL_RETRY_BACKOFF_SECONDS * (2**attempt),
        settings.CROWD_ETL_RETRY_BACKOFF_MAX_SECONDS,
    )
    return base + random.uniform(0, base * 0.1)


def run_etl_once(task, main_db, etl_type: str, request, build_etl) -> bool:
    """Runs an ETL window unless it already succeeded or is running. True if it ran."""
    params = request.model_dump()
    execution = find_etl_execution(main_db, etl_type, params)

    if execution is not None and not request.force:
        if execution_is_successful(execution):
            logging.info(f"Skipping ETL for {etl_type} with params {params}: already succeeded")
            return False
        if execution_is_running(execution):
            logging.info(
                f"Skipping ETL for {etl_type} with params {params}: "
                f"still running since {execution.updated_at or execution.created_at}"
            )
            return False

    if execution is None:
        execution = create_etl_execution(
            main_db, etl_type, user_id=request.user_id, params=params
        )
    else:
        mark_etl_execution(main_db, execution, ETL_STATUS_STARTED)

    # release the connection held by the refresh: a long ETL would come back to a closed one
    main_db.commit()

    try:
        result = build_etl().execute_once()
    except Exception as e:
        main_db.rollback()
        mark_etl_execution(main_db, execution, ETL_STATUS_FAILED, error=str(e))
        attempt = task.request.retries
        if attempt < settings.CROWD_ETL_MAX_RETRIES:
            countdown = etl_retry_countdown(attempt)
            logging.warning(
                f"ETL {etl_type} failed ({e}); retry {attempt + 1}/{settings.CROWD_ETL_MAX_RETRIES} "
                f"in {countdown:.0f}s. params={params}"
            )
            raise task.retry(
                exc=e, countdown=countdown, max_retries=settings.CROWD_ETL_MAX_RETRIES
            )
        logging.error(f"ETL {etl_type} failed after {attempt} retries: {e}. params={params}")
        raise

    if result != 0:
        # No data or a step returned False: left failed so the lookback re-dispatches it.
        logging.warning(f"ETL {etl_type} returned {result}; marked failed. params={params}")
        mark_etl_execution(main_db, execution, ETL_STATUS_FAILED, error=f"execute_once returned {result}")
        return True

    mark_etl_execution(main_db, execution, ETL_STATUS_SUCCESS)
    return True


@celery_app.task(
    name="platform.crowd.process_visitors_job",
    queue=CROWD_QUEUE_PROCESS_VISITORS_NAME,
    **DEFAULT_TASK_ARGS,
)
def process_visitors_job(self, request: ProcessVisitorsRequest) -> None:
    """
    Process one hourly window of visits / unique visitors per entity.
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())

    run_etl_once(
        self,
        main_db,
        CROWD_QUEUE_PROCESS_VISITORS_NAME,
        request,
        lambda: CrowdProcessVisitorsETL(
            request=request, main_db=main_db, realtime_db=realtime_db
        ),
    )


@celery_app.task(
    name="platform.crowd.classification_job",
    queue=CROWD_QUEUE_CLASSIFICATION_NAME,
    **DEFAULT_TASK_ARGS,
)
def classification_job(self, request: CrowdClassificationRequest) -> None:
    """
    Process one classification window.
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())

    run_etl_once(
        self,
        main_db,
        CROWD_QUEUE_CLASSIFICATION_NAME,
        request,
        lambda: CrowdClassificationETL(
            request=request, main_db=main_db, realtime_db=realtime_db
        ),
    )


@celery_app.task(
    name="platform.crowd.flows_municipality_job",
    queue=CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME,
    **DEFAULT_TASK_ARGS,
)
def flows_municipality_job(self, request: CrowdFlowsMunicipalityRequest) -> None:
    """
    Process one hourly window of municipality flows.
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())

    run_etl_once(
        self,
        main_db,
        CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME,
        request,
        lambda: CrowdFlowsMunicipalityETL(
            request=request, main_db=main_db, realtime_db=realtime_db
        ),
    )


@celery_app.task(
    name="platform.crowd.unique_visitors_job",
    queue=CROWD_QUEUE_UNIQUE_VISITORS_NAME,
    **DEFAULT_TASK_ARGS,
)
def unique_visitors_job(self, request: CrowdUniqueVisitorsRequest) -> None:
    """
    Process one unique-visitors window.
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())

    run_etl_once(
        self,
        main_db,
        CROWD_QUEUE_UNIQUE_VISITORS_NAME,
        request,
        lambda: CrowdUniqueVisitorsETL(
            request=request, main_db=main_db, realtime_db=realtime_db
        ),
    )


@celery_app.task(
    name="platform.crowd.process_visitors_all_job",
    queue=CROWD_QUEUE_PROCESS_VISITORS_ALL_NAME,
    **DEFAULT_TASK_ARGS,
)
def all_crowd_process_visitors_jobs(self, request: AllProcessVisitorsRequest = None) -> None:
    """
    Process an inference pipeline job
    """
    logging.info("Processing all crowd flows municipality jobs")
    main_db = next(get_db())
    req = request if request else AllProcessVisitorsRequest(
        start_date=None,
        end_date=None,
    )
    job = ProcessVisitorsAll(request=req, db=main_db)
    job.handle()



@celery_app.task(
    name="platform.crowd.classification_all_job",
    queue=CROWD_QUEUE_CLASIFICATION_ALL_NAME,
    **DEFAULT_TASK_ARGS,
)
def all_crowd_classification_jobs(self, request: AllCrowdClassificationRequest = None) -> None:
    """
    Process an inference pipeline job
    """
    logging.info("Processing all crowd classification jobs")
    main_db = next(get_db())
    req = request if request else AllCrowdClassificationRequest(
        start_date=None,
        end_date=None,
    )
    job = CrowdClassificationAll(request=req, db=main_db)
    job.handle()


@celery_app.task(
    name="platform.crowd.unique_visitors_all_job",
    queue=CROWD_QUEUE_UNIQUE_VISITORS_ALL_NAME,
    **DEFAULT_TASK_ARGS,
)
def all_crowd_unique_visitors_jobs(self, request: AllCrowdUniqueVisitorsRequest = None) -> None:
    """
    Process an inference pipeline job
    """
    logging.info("Processing all crowd unique visitors jobs")
    main_db = next(get_db())
    req = request if request else AllCrowdUniqueVisitorsRequest(
        start_date=None,
        end_date=None,
    )
    job = CrowdUniqueVisitorsAll(request=req, db=main_db)
    job.handle()


@celery_app.task(
    name="platform.crowd.flows_municipality_all_job",
    queue=CROWD_QUEUE_FLOWS_MUNICIPALITY_ALL_NAME,
    **DEFAULT_TASK_ARGS,
)
def all_crowd_flows_municipality_jobs(self, request: AllCrowdFlowsMunicipalityRequest = None) -> None:
    """
    Process an inference pipeline job
    """
    logging.info("Processing all crowd flows municipality jobs")
    main_db = next(get_db())
    req = request if request else AllCrowdFlowsMunicipalityRequest(
        start_date=None,
        end_date=None,
    )
    job = CrowdFlowsMunicipalityAll(request=req, db=main_db)
    job.handle()
    
# Periodic tasks
@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    logging.info("Setting up periodic crowd tasks")
    
    sender.add_periodic_task(
        settings.CROWD_PROCESS_VISITORS_INTERVAL,
        all_crowd_process_visitors_jobs.s(),
        name="Process all visitors",
    )
    sender.add_periodic_task(
        settings.CROWD_FLOWS_MUNICIPALITY_INTERVAL,
        all_crowd_flows_municipality_jobs.s(),
        name="Process all flows municipality",
    )
    
    logging.info("Setting up periodic crowd monthly classification tasks")
    sender.add_periodic_task(
        settings.CROWD_CLASSIFICATION_INTERVAL,
        all_crowd_classification_jobs.s(),
        name="Process all classification",
    )
    logging.info("Setting up periodic crowd unique visitors tasks")
    sender.add_periodic_task(
        settings.CROWD_UNIQUE_VISITORS_INTERVAL,
        all_crowd_unique_visitors_jobs.s(),
        name="Process all unique visitors",
    )

    

@celery_app.task(
    name="platform.crowd.classification_one_user_job",
    queue=CROWD_QUEUE_CLASSIFICATION_NAME,
    **DEFAULT_TASK_ARGS,
)
def classification_one_user_job(self, request: OneCrowdClassificationRequest) -> None:
    """
    Executes the classification job only for a specific user
    """
    logging.info(f"Executing crowd classification job for user_id: {request.user_id}")
    main_db = next(get_db())

    job = CrowdClassificationOneUser(request=request, db=main_db)
    job.generate_jobs()



# Task stub kept so /publish can serialize and route the message.
