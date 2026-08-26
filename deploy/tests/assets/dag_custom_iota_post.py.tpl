"""
Verification DAG — derived from the platform's Airflow DAG repository.

The verification suite renders this template (unique dag_id + fallback values
from tests.env), copies it into the running Airflow components, triggers a
single run, checks the entity appears in Orion-LD, and removes it again. It is
NOT a permanent DAG — do not add it to the git-synced DAGs repo.

The only differences from the original are: a templated dag_id, the Variable
fallback defaults baked in from the environment (so a missing Variable does not
silently fall back to a placeholder), and the test tags.
"""

from datetime import datetime, timedelta, timezone

import requests
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "platform",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    "__DAG_ID__",
    default_args=default_args,
    description="Platform verification: POST a measure to the IoT Agent JSON",
    schedule=None,  # manual trigger only
    catchup=False,
    tags=["test", "iota", "fiware", "pid-gijon-verification"],
)


def _cfg() -> dict:
    """Read configuration from Airflow Variables, with verification fallbacks."""
    return {
        "iota_url": Variable.get(
            "CUSTOM_IOTA_URL", default_var="__IOTA_URL__"
        ).rstrip("/"),
        "apikey": Variable.get("CUSTOM_IOTA_APIKEY", default_var="__IOTA_APIKEY__"),
        "datamodel": Variable.get("CUSTOM_DATAMODEL", default_var="__DATAMODEL__"),
        "tenant": Variable.get("CUSTOM_TENANT", default_var="__TENANT__"),
        "scope": Variable.get("CUSTOM_SCOPE", default_var="__SCOPE__"),
        "entity_name": Variable.get(
            "CUSTOM_ENTITY_NAME", default_var="__ENTITY_NAME__"
        ),
    }


def post_custom_entity(**_context):
    cfg = _cfg()

    if not cfg["apikey"]:
        raise ValueError("Missing Variable CUSTOM_IOTA_APIKEY (service group apikey).")
    if not cfg["tenant"]:
        raise ValueError("Missing Variable CUSTOM_TENANT (fiware-service / NGSI-LD tenant).")

    entity = cfg["entity_name"]
    url = f"{cfg['iota_url']}?i={entity}&k={cfg['apikey']}"

    headers = {
        "Content-Type": "application/json",
        "fiware-service": cfg["tenant"],
        "fiware-servicepath": cfg["scope"],
    }

    payload = {
        "value": 42,
        "TimeInstant": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    print(f"POST {cfg['iota_url']}?i={entity}&k=***")
    print(f"  fiware-service:     {cfg['tenant']}")
    print(f"  fiware-servicepath: {cfg['scope']}")
    print(f"  datamodel (type):   {cfg['datamodel']}")
    print(f"  body:               {payload}")

    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    if resp.status_code in (200, 201, 204):
        print(f"OK - measure sent for '{entity}' (HTTP {resp.status_code})")
        return "OK"

    raise RuntimeError(f"IoT Agent returned HTTP {resp.status_code}: {resp.text[:300]}")


post_task = PythonOperator(
    task_id="post_custom_entity",
    python_callable=post_custom_entity,
    dag=dag,
)
