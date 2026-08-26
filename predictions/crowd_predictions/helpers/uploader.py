#!/usr/bin/env python3
"""
Uploads entity CSVs to storage (S3/Minio) and publishes the importation job on
the platform queue - adapted 1:1 from the reference prediction ETL (helpers/uploader.py),
the "reliable" route already identified in
the datamodel documentation(§8): CSV -> S3 ->
platform.data.importation_job, instead of a direct POST to the IoT Agent (that one
loses data under load, confirmed in the internal documentation).

Difference from the original: the entity_type fallback is "CrowdFlowObserved"
instead of "ParkingSpot" (we have no real LIDAR emitting aggregated predictions
yet, only Smart Spot). The rest of the contract (queue message, naming
convention in storage) is identical so that both repos can be compared/kept the
same if they are ever split apart.
"""

import logging
import re
import time
from pathlib import Path

import requests

from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage

logger = logging.getLogger(__name__)

# CONTRACT WITH THE BACKEND, copied from EntityController::uploadDataToEntity in
# the backend: the prefix the importation job looks the CSV up under. If the
# backend ever changes it, the queue still answers 200 and this function still logs
# "OK" - the failure happens later, inside the consumer, invisible from here.
STORAGE_UPLOAD_PREFIX = "entities/uploads"

# The three columns the importation job REQUIRES in the wide CSV. Shared so the
# three producers (etl/crowd, etl/predict, fake_measures) cannot drift: a typo in one
# of these names is NOT rejected - it is imported as a different attribute and the
# entity ends up with a property nobody reads.
CSV_MANDATORY_COLUMNS = ("urn", "type", "timestamp")
# Unpacked so a producer can use them as keys and keep its own column ORDER: whether
# the consumer's parser reads by name or by position is not verified here, so the
# wire format is left exactly as it was.
URN_COLUMN, TYPE_COLUMN, TIMESTAMP_COLUMN = CSV_MANDATORY_COLUMNS


def upload_csv_via_s3_and_queue(csv_file_path: str, entity_id: str,
                                 tenant: str = None, scope: str = None) -> bool:
    """
    Uploads a CSV to storage and publishes the importation job on the platform queue.
    Replicates EntityController::uploadDataToEntity from the backend (same as
    the reference prediction ETL) - same task/params, same endpoint.
    """
    queue = settings.queue()
    queues_api_url = queue.QUEUES_CONSUMER_API_URL
    if not queues_api_url:
        logger.error("QUEUES_CONSUMER_API_URL is missing from the environment")
        return False

    # Mandatory in the consumer's schema, so it cannot be omitted from the message,
    # and it must not be guessed either: the consumer notifies that user on EVERY
    # published CSV. It grants no access - the tenant travels separately and nothing
    # cross-checks the two - it only decides who gets the notifications.
    if queue.QUEUES_CONSUMER_USER_ID is None:
        logger.error("QUEUES_CONSUMER_USER_ID is missing from the environment (the id of the "
                     "integrations service account) - not publishing")
        return False

    try:
        storage = get_storage()
    except ValueError as e:
        logger.error(f"Storage not configured: {e}")
        return False

    fiware = settings.fiware()
    tenant = tenant or fiware.FIWARE_TENANT
    scope = scope or fiware.FIWARE_SCOPE

    # An empty tenant is NOT publishable: the consumer drops any notification whose
    # tenant is empty (crud_entity.get_or_create_entity returns None), so the queue
    # answers 200, this returns True and NOTHING is ever created. Checked here and not
    # only in parse_target_specs because scripts/main.py does not go through it.
    if not (tenant or "").strip():
        logger.error("FIWARE_TENANT is empty - not publishing. The queue would accept the job "
                     "and the platform would create no entity, so the run would look successful.")
        return False

    csv_path = Path(csv_file_path)
    if not csv_path.exists():
        logger.error(f"File not found: {csv_file_path}")
        return False

    # settings.aether().ENTITY_TYPE and not the DEFAULT_ constant: reading the
    # constant meant that setting ENTITY_TYPE in the environment changed what
    # autodiscovery asked for but NOT what this fallback published.
    entity_type = settings.aether().ENTITY_TYPE
    if entity_id.startswith("urn:ngsi-ld:"):
        parts = entity_id.split(":")
        if len(parts) >= 3:
            entity_type = parts[2]

    timestamp = int(time.time())
    filename_without_ext = re.sub(r"[^A-Za-z0-9_\-]", "_", csv_path.stem)
    extension = csv_path.suffix.lstrip(".") or "csv"
    final_filename = f"{filename_without_ext}_{timestamp}.{extension}"
    storage_path = f"{STORAGE_UPLOAD_PREFIX}/{final_filename}"

    # The real backend, not the STORAGE_TYPE constant read at import time: if
    # someone changes the environment, the log says what is really being used.
    logger.info(f"Uploading {csv_path.name} via storage ({type(storage).__name__}) + queue...")
    logger.info(f"  Entity: {entity_id} ({entity_type})  ->  {storage_path}")

    try:
        storage.upload_file(storage_path, str(csv_path))
    except Exception as e:
        logger.error(f"  Failed uploading to storage: {e}")
        return False

    params = {
        "user_id": queue.QUEUES_CONSUMER_USER_ID,
        "storage_file_path": storage_path,
        "urn": entity_id,
        "tenant": tenant,
        "scope": scope,
        "type": entity_type,
    }
    message = {"task": "platform.data.importation_job", "params": params}

    try:
        response = requests.post(f"{queues_api_url}/publish", json=message, timeout=30)
    except requests.exceptions.RequestException as e:
        logger.error(f"  Error publishing on the queue: {e}")
        return False

    if response.status_code >= 400:
        logger.error(f"  Queue rejected the job (HTTP {response.status_code}): {response.text}")
        return False

    logger.info("  OK - importation job published")
    return True


def upload_csv_files(csv_files: list) -> dict:
    """
    Uploads the given CSVs (one per entity) via storage + queue. The file name
    without extension is the URN of the entity.

    An EXPLICIT list and not a glob of the directory: the output directories are not
    cleaned between runs, so globbing republishes the CSVs of previous runs. A sensor
    that stops reporting keeps "predicting" yesterday's numbers for ever, every run,
    counted as a success.
    """
    results = {"successful": [], "failed": []}
    for csv_file in [Path(f) for f in csv_files]:

        entity_id = csv_file.stem
        ok = upload_csv_via_s3_and_queue(str(csv_file), entity_id)
        (results["successful"] if ok else results["failed"]).append(str(csv_file))

    logger.info(f"Upload summary: {len(results['successful'])} OK, {len(results['failed'])} failed")
    return results
