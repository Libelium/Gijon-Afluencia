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
from models.crud.crud_etl_executions import get_etl_execution_with_specific_params, create_etl_execution

@celery_app.task(
    name="platform.crowd.process_visitors_job",
    queue=CROWD_QUEUE_PROCESS_VISITORS_NAME,
    **DEFAULT_TASK_ARGS,
)
def process_visitors_job(self, request: ProcessVisitorsRequest) -> None:
    """
    Process an inference pipeline job
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())
    
    previous_etl = get_etl_execution_with_specific_params(
        main_db,
        etl_type=CROWD_QUEUE_PROCESS_VISITORS_NAME,
        params=request.model_dump(),
    )
    
    if (not previous_etl) or request.force:
        if not previous_etl:
            create_etl_execution(
                main_db,
                CROWD_QUEUE_PROCESS_VISITORS_NAME,
                user_id=request.user_id,
                params=request.model_dump(),
            )
        
        etl = CrowdProcessVisitorsETL(request=request, main_db=main_db, realtime_db=realtime_db)
        etl.execute_once()
        
    else:
        logging.info(f"Skipping ETL for {CROWD_QUEUE_PROCESS_VISITORS_NAME} with params {request.model_dump()}")
    
@celery_app.task(
    name="platform.crowd.classification_job",
    queue=CROWD_QUEUE_CLASSIFICATION_NAME,
    **DEFAULT_TASK_ARGS,
)
def classification_job(self, request: CrowdClassificationRequest) -> None:
    """
    Process an inference pipeline job
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())
    
    previous_etl = get_etl_execution_with_specific_params(
        main_db,
        etl_type=CROWD_QUEUE_CLASSIFICATION_NAME,
        params=request.model_dump(),
    )
    
    if (not previous_etl) or request.force:
        if not previous_etl:
            create_etl_execution(
                main_db,
                CROWD_QUEUE_CLASSIFICATION_NAME,
                user_id=request.user_id,
                params=request.model_dump(),
            )
        
        etl = CrowdClassificationETL(request=request, main_db=main_db, realtime_db=realtime_db)
        etl.execute_once()
        
    else:
        logging.info(f"Skipping ETL for {CROWD_QUEUE_CLASSIFICATION_NAME} with params {request.model_dump()}")
    
@celery_app.task(
    name="platform.crowd.flows_municipality_job",
    queue=CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME,
    **DEFAULT_TASK_ARGS,
)
def flows_municipality_job(self, request: CrowdFlowsMunicipalityRequest) -> None:
    """
    Process an inference pipeline job
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())
    
    previous_etl = get_etl_execution_with_specific_params(
        main_db,
        etl_type=CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME,
        params=request.model_dump(),
    )
    
    if (not previous_etl) or request.force:
        if not previous_etl:
            create_etl_execution(
                main_db,
                CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME,
                user_id=request.user_id,
                params=request.model_dump(),
            )

        etl = CrowdFlowsMunicipalityETL(request=request, main_db=main_db, realtime_db=realtime_db)
        etl.execute_once()
            
    else:
        logging.info(f"Skipping ETL for {CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME} with params {request.model_dump()}")

@celery_app.task(
    name="platform.crowd.unique_visitors_job",
    queue=CROWD_QUEUE_UNIQUE_VISITORS_NAME,
    **DEFAULT_TASK_ARGS,
)
def unique_visitors_job(self, request: CrowdUniqueVisitorsRequest) -> None:
    """
    Process unique visitors
    """
    main_db = next(get_db())
    realtime_db = next(get_db_realtime())
    
    previous_etl = get_etl_execution_with_specific_params(
        main_db,
        etl_type=CROWD_QUEUE_UNIQUE_VISITORS_NAME,
        params=request.model_dump(),
    )
    
    if (not previous_etl) or request.force:
        if not previous_etl:
            create_etl_execution(
                main_db,
                CROWD_QUEUE_UNIQUE_VISITORS_NAME,
                user_id=request.user_id,
                params=request.model_dump(),
            )

        etl = CrowdUniqueVisitorsETL(request=request, main_db=main_db, realtime_db=realtime_db)
        etl.execute_once()
            
    else:
        logging.info(f"Skipping ETL for {CROWD_QUEUE_UNIQUE_VISITORS_NAME} with params {request.model_dump()}")
    
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
