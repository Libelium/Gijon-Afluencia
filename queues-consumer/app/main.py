import os
import subprocess
import sys
import time

import uvicorn
from api import application
from config.config import settings, storage
from config.logging import appLogging as logging
from config.queue_worker_type import WorkerType

if __name__ == "__main__":
    if settings.PROMETHEUS_MULTIPROC_DIR:
        os.makedirs(settings.PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
        # Must be in os.environ (not just the Python settings object) before
        # worker subprocesses are spawned — prometheus_client reads this env var
        # at import time to activate multiprocess mode.  Workers inherit the
        # environment of this parent process, so setting it here is enough.
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = settings.PROMETHEUS_MULTIPROC_DIR


    # Check if running in DLQ recovery mode
    if settings.WORKER_TYPE == WorkerType.DLQ_RECOVERY:
        logging.info("DLQ Recovery Job starting")
        
        from services.dlq_recovery import run_dlq_recovery

        try:
            run_dlq_recovery()
        except KeyboardInterrupt:
            logging.info("DLQ Recovery Job interrupted by user")
            sys.exit(0)
        except Exception as e:
            logging.error(f"DLQ Recovery Job failed: {e}")
            sys.exit(1)

    wait_for = []

    num_workers = settings.QUEUE_CONSUMER_WORKERS
    concurrency = settings.WORKER_CONCURRENCY

    logging.info(f"Starting {num_workers} workers with concurrency {concurrency}...")
    workers = [
        subprocess.Popen(
            [
                "python",
                "-m",
                "celery",
                "-A",
                "config.celery",
                "worker",
                "--loglevel=INFO",
                f"--concurrency={concurrency}",
                "-n",
                f"worker@%h-{i}",
            ],
            cwd="/code/app",
        )
        for i in range(num_workers)
    ]
    wait_for.extend(workers)

    # Scheduler for periodic tasks
    if settings.LAUNCH_CELERY_SCHEDULER:
        # give time to workers to set up and avoid
        # celerybeat starting before workers (if this happens,
        # periodic tasks will be executed repeatedly)
        logging.info("Starting scheduler...")
        # Not the most elegant way to wait for workers to start
        time.sleep(10)
        scheduler = subprocess.Popen(
            ["python", "-m", "celery", "-A", "config.celery", "beat", "--loglevel=INFO"],
            cwd="/code/app",
        )
        wait_for.append(scheduler)

    if settings.LAUNCH_UVICORN:
        logging.info("Starting Uvicorn server...")
        uvicorn.run(
            "main:application",
            app_dir="/code/app",
            port=8001,
            host="0.0.0.0",
            log_level="info",
            workers=settings.UVICORN_WORKERS,
            # accept headers so it respects protocol in the redirections
            proxy_headers=True,
            forwarded_allow_ips="*"
        )

    # wait for all processes to finish,
    # which will never happen as they are daemon threads
    # if uvicorn is running, this part will never be reached
    # unless uvicorn is stopped
    for process in wait_for:
        process.wait()
