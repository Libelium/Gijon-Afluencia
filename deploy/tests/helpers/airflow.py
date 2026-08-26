"""
Airflow 3 client for the verification suite.

Covers exactly what test_07_airflow needs: authenticate against the api-server
(JWT via /auth/token), manage Variables, deploy a DAG file into the running
components with `kubectl cp` (the chart syncs DAGs from git, so there is no
upload API), and drive a single DAG run to completion.

Every REST call has a timeout and TLS follows the suite settings. kubectl
helpers never raise — they return (ok, reason) — so the stage degrades into a
clear failure/skip instead of a traceback when Airflow or the cluster is absent.
"""

import time
from typing import List, Optional, Tuple

import requests

from . import kube
from .api import http_request
from .config import config

# Official chart components that need the DAG file on disk. With CeleryExecutor
# the dag-processor parses/serializes the DAG and the worker executes the task,
# so both must have it; the container name matches the component name.
DAG_COMPONENTS = ("dag-processor", "worker")

TERMINAL_STATES = ("success", "failed")


class AirflowError(RuntimeError):
    """An Airflow REST call failed in a way the check should report."""


class AirflowClient:
    """Thin Airflow 3 REST client (api-server, /api/v2) with JWT auth."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._token: Optional[str] = None

    # --- auth ----------------------------------------------------------------

    def login(self) -> None:
        """Obtain a JWT from the api-server's /auth/token endpoint."""
        response = http_request(
            "POST",
            f"{self.base_url}/auth/token",
            json={"username": self._username, "password": self._password},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code in (401, 403):
            raise AirflowError(
                f"Airflow login rejected (HTTP {response.status_code}) for user "
                f"'{self._username}' — check AIRFLOW_USERNAME / AIRFLOW_PASSWORD "
                "(the chart's webserver.defaultUser)."
            )
        if not 200 <= response.status_code < 300:
            raise AirflowError(
                f"Airflow /auth/token returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
        token = response.json().get("access_token")
        if not token:
            raise AirflowError("Airflow /auth/token gave no access_token")
        self._token = token

    def _headers(self) -> dict:
        if not self._token:
            self.login()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        return http_request(
            method, f"{self.base_url}{path}", headers=self._headers(), **kwargs
        )

    # --- variables -----------------------------------------------------------

    def set_variable(self, key: str, value: str) -> None:
        """Create or update an Airflow Variable (POST, then PATCH on conflict)."""
        body = {"key": key, "value": value, "description": "platform verification"}
        response = self._request("POST", "/api/v2/variables", json=body)
        if response.status_code == 409:
            response = self._request("PATCH", f"/api/v2/variables/{key}", json=body)
        if not 200 <= response.status_code < 300:
            raise AirflowError(
                f"Could not set Variable '{key}' (HTTP {response.status_code}): "
                f"{response.text[:200]}"
            )

    def delete_variable(self, key: str) -> bool:
        """Delete a Variable. Returns False on error (teardown is best-effort)."""
        try:
            response = self._request("DELETE", f"/api/v2/variables/{key}")
        except Exception:
            return False
        return response.status_code in (200, 204, 404)

    # --- dags ----------------------------------------------------------------

    def wait_for_dag(self, dag_id: str, attempts: int, interval: float) -> bool:
        """Poll until the dag-processor has registered the DAG (GET succeeds)."""
        for attempt in range(attempts):
            if attempt:
                time.sleep(interval)
            response = self._request("GET", f"/api/v2/dags/{dag_id}")
            if response.status_code == 200:
                return True
        return False

    def unpause_dag(self, dag_id: str) -> None:
        response = self._request(
            "PATCH",
            f"/api/v2/dags/{dag_id}",
            params={"update_mask": "is_paused"},
            json={"is_paused": False},
        )
        if not 200 <= response.status_code < 300:
            raise AirflowError(
                f"Could not unpause DAG '{dag_id}' (HTTP {response.status_code}): "
                f"{response.text[:200]}"
            )

    def trigger_dag_run(self, dag_id: str, run_id: str) -> str:
        """Trigger a single manual run; returns the dag_run_id."""
        response = self._request(
            "POST",
            f"/api/v2/dags/{dag_id}/dagRuns",
            json={"dag_run_id": run_id, "logical_date": None, "conf": {}},
        )
        if not 200 <= response.status_code < 300:
            raise AirflowError(
                f"Could not trigger DAG '{dag_id}' (HTTP {response.status_code}): "
                f"{response.text[:200]}"
            )
        return response.json().get("dag_run_id", run_id)

    def wait_for_run(
        self, dag_id: str, run_id: str, attempts: int, interval: float
    ) -> str:
        """Poll the run until it reaches a terminal state; returns the last state."""
        state = "unknown"
        for attempt in range(attempts):
            if attempt:
                time.sleep(interval)
            response = self._request(
                "GET", f"/api/v2/dags/{dag_id}/dagRuns/{run_id}"
            )
            if response.status_code != 200:
                continue
            state = response.json().get("state", "unknown")
            if state in TERMINAL_STATES:
                return state
        return state

    def delete_dag(self, dag_id: str) -> bool:
        """Delete the DAG's metadata/history. Returns False on error."""
        try:
            response = self._request("DELETE", f"/api/v2/dags/{dag_id}")
        except Exception:
            return False
        return response.status_code in (200, 204, 404)


# --- DAG file deployment via kubectl cp --------------------------------------

def dags_folder(namespace: str) -> Optional[str]:
    """Resolve core.dags_folder from a dag-processor pod (git-sync target)."""
    pods = kube.pods_by_label("component=dag-processor", namespace)
    if not pods:
        return None
    ok, out = kube.exec_capture(
        namespace, pods[0],
        ["airflow", "config", "get-value", "core", "dags_folder"],
        container="dag-processor",
    )
    return out.strip() if ok and out.strip() else None


def deploy_dag(
    local_path: str, remote_filename: str, namespace: str, folder: str
) -> Tuple[bool, str]:
    """Copy the DAG file into every component that needs it.

    Succeeds if at least the dag-processor got it (so the DAG registers); copies
    to workers too so the task can execute. Returns (ok, reason-if-not).
    """
    remote_path = f"{folder.rstrip('/')}/{remote_filename}"
    copied_dag_processor = False
    errors: List[str] = []
    for component in DAG_COMPONENTS:
        pods = kube.pods_by_label(f"component={component}", namespace)
        if not pods:
            errors.append(f"no Running '{component}' pod found")
            continue
        for pod in pods:
            ok, reason = kube.cp_to_pod(
                local_path, namespace, pod, remote_path, container=component
            )
            if ok and component == "dag-processor":
                copied_dag_processor = True
            elif not ok:
                errors.append(f"{component}/{pod}: {reason}")
    if not copied_dag_processor:
        return False, "; ".join(errors) or "DAG file could not be copied"
    return True, "; ".join(errors)


def remove_dag(remote_filename: str, namespace: str, folder: str) -> None:
    """Best-effort removal of the DAG file from every component (teardown)."""
    remote_path = f"{folder.rstrip('/')}/{remote_filename}"
    for component in DAG_COMPONENTS:
        for pod in kube.pods_by_label(f"component={component}", namespace):
            kube.exec_capture(
                namespace, pod, ["rm", "-f", remote_path], container=component
            )
