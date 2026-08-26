"""
Stage 7 — Airflow (optional).

End-to-end check of an installed Airflow 3: deploy a one-shot DAG, run it once,
and confirm its side effect lands in the platform. The DAG is a copy of
airflow/dag_custom_iota_post.py — it POSTs a measure to the IoT Agent JSON,
which provisions/updates an NGSI-LD entity in Orion-LD under the test tenant.

Flow (one check per hop so the report pinpoints the break):

  login (api-server JWT) → create Variables → deploy DAG (kubectl cp into the
  dag-processor + workers; Airflow 3 has no DAG upload API) + trigger one run →
  entity appears in Orion-LD (platform realtime API)

Everything created is torn down by the module fixture: the DAG file is removed
from the pods, the DAG metadata is deleted via the API, and every Variable is
deleted — whether or not the checks pass.

The whole stage skips when AIRFLOW_URL is unset (Airflow is an optional add-on,
not part of the base installer).
"""

import time
from pathlib import Path

import pytest

from helpers import airflow, api, session
from helpers.airflow import AirflowClient, AirflowError
from helpers.api import EntityIdentifier
from helpers.config import config
from helpers.report import fail, require

SECTION = "Airflow (custom_iota_post)"

# Airflow Variables the DAG reads (Admin -> Variables), set from tests.env.
_VARIABLES = {
    "CUSTOM_IOTA_URL": config.airflow_var_iota_url,
    "CUSTOM_IOTA_APIKEY": config.airflow_var_iota_apikey,
    "CUSTOM_DATAMODEL": config.airflow_var_datamodel,
    "CUSTOM_TENANT": config.airflow_var_tenant,
    "CUSTOM_SCOPE": config.airflow_var_scope,
    "CUSTOM_ENTITY_NAME": config.airflow_var_entity_name,
}

# Shared across checks (the suite's create-as-a-check pattern; see helpers.session).
_STATE = {
    "client": None,      # AirflowClient
    "dag_id": None,      # str
    "dag_file": None,    # remote filename copied into the pods
    "folder": None,      # resolved dags_folder
    "variables_set": [], # keys actually created (for teardown)
}


def _skip_unless_airflow():
    if not config.airflow_url:
        pytest.skip("AIRFLOW_URL not set in tests.env (Airflow is optional)")


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    """Best-effort teardown: remove DAG file, delete DAG metadata and Variables."""
    yield
    client = _STATE["client"]
    if _STATE["dag_file"] and _STATE["folder"]:
        airflow.remove_dag(_STATE["dag_file"], config.airflow_namespace, _STATE["folder"])
    if client and _STATE["dag_id"]:
        client.delete_dag(_STATE["dag_id"])
    if client:
        for key in _STATE["variables_set"]:
            client.delete_variable(key)


@pytest.mark.check(
    id="airflow-login",
    title="Airflow api-server reachable and admin login works",
    section=SECTION,
)
@pytest.mark.api
def test_airflow_login():
    require("prereq-config")
    _skip_unless_airflow()
    if not config.airflow_username or not config.airflow_password:
        fail(
            "AIRFLOW_USERNAME / AIRFLOW_PASSWORD are not set",
            "Fill them in environments/<name>/tests.env (or config.env before "
            "generating it) with the Airflow admin user — the chart's "
            "webserver.defaultUser.username / .password.",
        )
    client = AirflowClient(
        config.airflow_url, config.airflow_username, config.airflow_password
    )
    try:
        client.login()
    except AirflowError as exc:
        fail(
            str(exc),
            f"Confirm {config.airflow_url} fronts airflow-api-server and the route "
            "is published (HTTPRoute/Ingress).",
            f"Check the pod: kubectl logs -n {config.airflow_namespace} "
            "deploy/airflow-api-server",
        )
    _STATE["client"] = client


@pytest.mark.check(
    id="airflow-variables",
    title="DAG Variables created (CUSTOM_IOTA_* / CUSTOM_TENANT / ...)",
    section=SECTION,
)
@pytest.mark.api
def test_create_variables():
    require("airflow-login")
    missing = [
        name
        for name, value in (
            ("AIRFLOW_VAR_IOTA_APIKEY", config.airflow_var_iota_apikey),
            ("AIRFLOW_VAR_TENANT", config.airflow_var_tenant),
        )
        if not value
    ]
    if missing:
        fail(
            "Required Airflow test settings are empty: " + ", ".join(missing),
            "The DAG POSTs to the IoT Agent with a service-group apikey and an "
            "NGSI-LD tenant — there is no safe default for either.",
            "Set them in environments/<name>/tests.env (AIRFLOW_VAR_IOTA_APIKEY, "
            "AIRFLOW_VAR_TENANT), or in config.env before generating it.",
        )

    client = _STATE["client"]
    for key, value in _VARIABLES.items():
        try:
            client.set_variable(key, value)
        except AirflowError as exc:
            fail(str(exc))
        _STATE["variables_set"].append(key)


@pytest.mark.check(
    id="airflow-dag-run",
    title="DAG deployed, triggered once and the run succeeds",
    section=SECTION,
)
@pytest.mark.api
@pytest.mark.kubernetes
def test_deploy_and_run_dag(tmp_path):
    require("airflow-variables", "prereq-cluster")
    client = _STATE["client"]

    dag_id = f"pid_gijon_verify_iota_post_{int(time.time())}"
    dag_file = f"{dag_id}.py"
    _STATE["dag_id"] = dag_id
    _STATE["dag_file"] = dag_file

    # Render the DAG template (unique id + fallback defaults from the env).
    template_path = Path(__file__).parent / "assets" / "dag_custom_iota_post.py.tpl"
    source = template_path.read_text(encoding="utf-8")
    replacements = {
        "__DAG_ID__": dag_id,
        "__IOTA_URL__": config.airflow_var_iota_url,
        "__IOTA_APIKEY__": config.airflow_var_iota_apikey,
        "__DATAMODEL__": config.airflow_var_datamodel,
        "__TENANT__": config.airflow_var_tenant,
        "__SCOPE__": config.airflow_var_scope,
        "__ENTITY_NAME__": config.airflow_var_entity_name,
    }
    for token, value in replacements.items():
        source = source.replace(token, value)
    local_dag = tmp_path / dag_file
    local_dag.write_text(source, encoding="utf-8")

    # Resolve the DAGs folder and copy the file into the running components.
    folder = airflow.dags_folder(config.airflow_namespace)
    if not folder:
        fail(
            "Could not resolve Airflow's dags_folder (no Running dag-processor pod?)",
            f"kubectl get pods -n {config.airflow_namespace} -l component=dag-processor",
            "Airflow 3 splits parsing into the dag-processor — it must be running.",
        )
    _STATE["folder"] = folder

    ok, reason = airflow.deploy_dag(
        str(local_dag), dag_file, config.airflow_namespace, folder
    )
    if not ok:
        fail(
            f"Could not copy the DAG into the Airflow pods: {reason}",
            f"The components sync DAGs from git into {folder}; the suite copies a "
            "throwaway DAG there with kubectl cp. Confirm kubectl can exec/cp into "
            f"namespace '{config.airflow_namespace}' and that the pods ship tar.",
        )

    # The dag-processor parses on its own interval; wait for the DAG to register.
    attempts = max(config.propagation_attempts, 12)
    if not client.wait_for_dag(dag_id, attempts, config.propagation_interval):
        fail(
            f"DAG '{dag_id}' did not appear after {attempts} polls",
            "The file was copied but the dag-processor has not parsed/serialized it "
            "yet (or rejected it). Check: kubectl logs -n "
            f"{config.airflow_namespace} deploy/airflow-dag-processor",
            "git-sync may also overwrite the DAGs folder on its next sync — if this "
            "is flaky, raise PROPAGATION_INTERVAL_SECONDS or the git-sync wait.",
        )

    try:
        client.unpause_dag(dag_id)
        run_id = client.trigger_dag_run(dag_id, f"{dag_id}_run")
    except AirflowError as exc:
        fail(str(exc))

    state = client.wait_for_run(dag_id, run_id, attempts, config.propagation_interval)
    if state != "success":
        fail(
            f"DAG run finished in state '{state}' (expected 'success')",
            "The task POSTs to the IoT Agent. A failed run usually means the "
            "Variables are wrong or the IoT Agent is unreachable from the worker.",
            f"Inspect the run in the Airflow UI ({config.airflow_url}) or: "
            f"kubectl logs -n {config.airflow_namespace} -l component=worker",
        )


@pytest.mark.check(
    id="airflow-entity",
    title="Entity provisioned in Orion-LD by the IoT Agent",
    section=SECTION,
)
@pytest.mark.api
def test_entity_created_in_orion():
    require("airflow-dag-run", "auth-login")

    tenant = config.airflow_var_tenant
    scope = config.airflow_var_scope or "/"
    entity_name = config.airflow_var_entity_name
    candidates = [
        f"urn:ngsi-ld:{config.airflow_var_datamodel}:{entity_name}",
        entity_name,
    ]

    last_checked = None
    for attempt in range(max(config.propagation_attempts, 8)):
        if attempt:
            time.sleep(config.propagation_interval)
        for urn in candidates:
            last_checked = urn
            properties = api.read_entity_properties(
                session.token, EntityIdentifier(urn=urn, tenant=tenant, scope=scope)
            )
            if properties:
                return

    fail(
        f"No entity for the DAG found in Orion-LD (tenant '{tenant}', tried: "
        f"{', '.join(candidates)})",
        "The DAG run succeeded but the IoT Agent did not surface an entity. The "
        "entity id depends on the service group bound to the apikey — confirm the "
        "group's entity_type matches AIRFLOW_VAR_DATAMODEL.",
        f"Check the pipeline: kubectl logs -n {config.platform_namespace} "
        f"deploy/iot-agent-json ; kubectl logs -n {config.platform_namespace} "
        "deploy/orion-ld",
    )
