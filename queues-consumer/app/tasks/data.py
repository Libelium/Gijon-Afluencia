from config.celery import DEFAULT_TASK_ARGS
from config.celery import app as celery_app
from config.config import settings
from config.logging import appLogging as logging
from config.queues import DATA_IMPORTATION_QUEUE_NAME
from jobs.data.data_importation.data_importation_job import DataImportationJob
from schemas.data_importation_request import DataImportationRequest


@celery_app.task(
    name="platform.data.importation_job",
    queue=DATA_IMPORTATION_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=settings.QUEUE_TASK_CONFIG.get_config_param(
        DATA_IMPORTATION_QUEUE_NAME, "timeout"
    ),
)
def data_importation_job(self, request: DataImportationRequest) -> None:
    """
    Process a generic data importation job
    """
    job = DataImportationJob(request=request)
    job.handle()
