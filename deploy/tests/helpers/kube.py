"""
Thin kubectl wrapper for the cluster-level checks.

Everything is read-only (get/version). Each call has a timeout so a broken
kubeconfig or unreachable API server fails fast with a clear message instead
of hanging the suite.
"""

import json
import shutil
import subprocess
from typing import Any, List, Optional, Tuple

from .config import config

KUBECTL_TIMEOUT_SECONDS = 30


class KubectlError(RuntimeError):
    """kubectl invocation failed (binary missing, bad context, API unreachable...)."""


def _base_command() -> List[str]:
    command = ["kubectl"]
    if config.kube_context:
        command += ["--context", config.kube_context]
    return command


def _run(args: List[str]) -> subprocess.CompletedProcess:
    if shutil.which("kubectl") is None:
        raise KubectlError("kubectl is not installed or not on PATH")
    try:
        return subprocess.run(
            _base_command() + args,
            capture_output=True,
            text=True,
            timeout=KUBECTL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise KubectlError(
            f"kubectl timed out after {KUBECTL_TIMEOUT_SECONDS}s — is the cluster reachable?"
        ) from exc


def cluster_reachable() -> Tuple[bool, str]:
    """Check API server connectivity. Returns (ok, reason-if-not)."""
    try:
        result = _run(["version", "--output", "json"])
    except KubectlError as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, result.stderr.strip().splitlines()[-1] if result.stderr else "unknown error"
    return True, ""


def get_json(*args: str) -> Optional[Any]:
    """Run `kubectl get ... -o json`. Returns parsed JSON, or None on NotFound."""
    result = _run(["get", *args, "-o", "json"])
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "NotFound" in stderr or "the server doesn't have a resource type" in stderr:
            return None
        raise KubectlError(f"kubectl get {' '.join(args)} failed: {stderr}")
    return json.loads(result.stdout)


def list_items(*args: str) -> List[dict]:
    """Run `kubectl get ... -o json` for a collection; returns .items (or [])."""
    data = get_json(*args)
    if data is None:
        return []
    return data.get("items", [])


def api_resource_exists(resource: str) -> bool:
    """Check whether a resource type (e.g. 'httproutes') is served by the cluster."""
    result = _run(["api-resources", "--no-headers"])
    if result.returncode != 0:
        raise KubectlError(f"kubectl api-resources failed: {result.stderr.strip()}")
    return any(line.split()[0] == resource for line in result.stdout.splitlines() if line.split())


def condition(obj: dict, condition_type: str) -> Optional[dict]:
    """Find a status condition by type on any Kubernetes object."""
    for cond in obj.get("status", {}).get("conditions", []):
        if cond.get("type") == condition_type:
            return cond
    return None


def condition_true(obj: dict, condition_type: str) -> bool:
    cond = condition(obj, condition_type)
    return cond is not None and cond.get("status") == "True"


# --- IoT Agent device API-key discovery --------------------------------------
# The "k" query parameter a device uses to push data is the API key of the IoT
# Agent service group it was provisioned under. A platform can define several
# groups for the same entity type, so the key is only unambiguous for an
# already-provisioned device. We read it from the IoT Agent's northbound admin
# API (GET /iot/devices/<id>), which returns the exact key the device uses and
# needs no database credentials. The admin port (4041) is cluster-internal, so
# we run a tiny Node client inside the IoT Agent pod (the image ships Node).

_DEVICE_APIKEY_NODE_SCRIPT = """
const http = require("http");
const [id, service, servicepath] = process.argv.slice(1);
const options = {
  host: "localhost",
  port: 4041,
  path: "/iot/devices/" + encodeURIComponent(id),
  headers: { "fiware-service": service, "fiware-servicepath": servicepath || "/" },
};
http
  .get(options, (res) => {
    let body = "";
    res.on("data", (chunk) => (body += chunk));
    res.on("end", () => {
      if (res.statusCode !== 200) return process.exit(2);
      try {
        const device = JSON.parse(body);
        if (device.apikey) process.stdout.write(String(device.apikey));
        else process.exit(3);
      } catch (e) {
        process.exit(4);
      }
    });
  })
  .on("error", () => process.exit(5));
"""


def pods_by_label(label_selector: str, namespace: str) -> List[str]:
    """Names of Running pods matching a label selector (e.g. 'component=worker')."""
    pods = list_items(
        "pods", "-n", namespace, "-l", label_selector,
        "--field-selector=status.phase=Running",
    )
    return [pod["metadata"]["name"] for pod in pods]


def exec_capture(
    namespace: str, pod: str, command: List[str], container: Optional[str] = None
) -> Tuple[bool, str]:
    """Run a command inside a pod. Returns (ok, stdout-or-stderr).

    Never raises KubectlError to callers — returns (False, reason) instead, so
    Airflow checks degrade gracefully when the cluster is unreachable.
    """
    args = ["exec", "-n", namespace, pod]
    if container:
        args += ["-c", container]
    args += ["--", *command]
    try:
        result = _run(args)
    except KubectlError as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()
    return True, result.stdout


def cp_to_pod(
    local_path: str, namespace: str, pod: str, remote_path: str,
    container: Optional[str] = None,
) -> Tuple[bool, str]:
    """Copy a local file into a pod with `kubectl cp`. Returns (ok, reason)."""
    args = ["cp", local_path, f"{namespace}/{pod}:{remote_path}"]
    if container:
        args += ["-c", container]
    try:
        result = _run(args)
    except KubectlError as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()
    return True, ""


def _deployment_pod(deployment: str, namespace: str) -> Optional[str]:
    """Return the name of a Running pod backing a deployment, or None.

    Resolves the pod via the deployment's own label selector, so it does not
    depend on the Helm release name baked into the pod labels.
    """
    dep = get_json("deployment", deployment, "-n", namespace)
    if dep is None:
        return None
    selector = dep.get("spec", {}).get("selector", {}).get("matchLabels", {})
    if not selector:
        return None
    label_arg = ",".join(f"{key}={value}" for key, value in selector.items())
    pods = list_items(
        "pods", "-n", namespace, "-l", label_arg,
        "--field-selector=status.phase=Running",
    )
    for pod in pods:
        return pod["metadata"]["name"]
    return None


def discover_device_apikey(
    serial: str,
    service: str,
    namespace: str,
    deployment: str = "iot-agent-json",
    servicepath: str = "/",
) -> Optional[str]:
    """Discover the data API key of a provisioned device via the IoT Agent.

    Returns the key, or None when it cannot be determined (kubectl unavailable,
    IoT Agent not deployed, device not provisioned yet). Never raises, so the
    data-path checks can fall back to skipping with instructions.
    """
    if not serial or not service:
        return None
    try:
        pod = _deployment_pod(deployment, namespace)
        if not pod:
            return None
        result = _run(
            ["exec", "-n", namespace, pod, "--",
             "node", "-e", _DEVICE_APIKEY_NODE_SCRIPT,
             serial, service, servicepath or "/"]
        )
    except KubectlError:
        return None
    if result.returncode != 0:
        return None
    key = result.stdout.strip()
    return key or None
