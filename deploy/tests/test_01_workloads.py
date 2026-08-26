"""
Stage 1 — cluster workloads.

Checks that every deployed chart's pods are actually running: the data layer
(PostgreSQL, MongoDB, RabbitMQ, MinIO — only those deployed as bundled charts)
and every pid-gijon-core component. Also scans for classic first-install pod
pathologies (ImagePullBackOff, Pending on storage, CrashLoopBackOff) and turns
them into targeted advice.
"""

import base64

import pytest

from helpers import kube, report
from helpers.config import config
from helpers.report import fail, require

SECTION = "Cluster workloads"

# pid-gijon-core deployments, named by the kebab-case of the chart component key.
PLATFORM_DEPLOYMENTS = [
    "aether-link",
    "carrot",
    "cb-consumer",
    "fiware-manager",
    "generic-consumer",
    "iot-agent-json",
    "keycloak",
    "orion-ld",
    "web-back",
]


def _pod_problems(namespace: str):
    """Return [(pod, problem, advice)] for pods that are not healthy."""
    problems = []
    for pod in kube.list_items("pods", "-n", namespace):
        name = pod["metadata"]["name"]
        phase = pod["status"].get("phase", "Unknown")
        if phase == "Succeeded":
            continue

        if phase == "Pending":
            advice = (
                f"kubectl describe pod -n {namespace} {name} — look at Events. "
                "Common causes: no default StorageClass (PVC stuck Pending), "
                "unschedulable nodes (resources/taints)."
            )
            problems.append((name, "Pending", advice))
            continue

        for status in pod["status"].get("containerStatuses", []):
            waiting = status.get("state", {}).get("waiting") or {}
            waiting_reason = waiting.get("reason", "")
            if waiting_reason in ("ImagePullBackOff", "ErrImagePull"):
                problems.append(
                    (
                        name,
                        waiting_reason,
                        "The image cannot be pulled. Check IMAGE_REGISTRY in "
                        "config.env, the image tag, and registry credentials "
                        "(imagePullSecrets).",
                    )
                )
            elif waiting_reason == "CrashLoopBackOff":
                problems.append(
                    (
                        name,
                        "CrashLoopBackOff",
                        f"kubectl logs -n {namespace} {name} --previous — usually "
                        "bad credentials/hostnames in the generated values, or a "
                        "dependency (DB/broker) that is not up yet.",
                    )
                )
            elif not status.get("ready", False) and phase == "Running":
                problems.append(
                    (
                        name,
                        "container not Ready",
                        f"kubectl describe pod -n {namespace} {name} — the "
                        "readiness probe is failing; check the container logs.",
                    )
                )
    return problems


def _check_namespace_workloads(namespace: str, friendly_name: str, install_hint: str):
    require("prereq-cluster")

    pods = kube.list_items("pods", "-n", namespace)
    if not pods:
        fail(
            f"No pods found in namespace '{namespace}'",
            f"{friendly_name} does not appear to be deployed.",
            install_hint,
        )

    problems = _pod_problems(namespace)
    if problems:
        lines = [f"{pod}: {problem}" for pod, problem, _ in problems]
        advice = [advice for _, _, advice in problems]
        fail(
            f"{friendly_name}: unhealthy pods in '{namespace}':\n" + "\n".join(lines),
            *dict.fromkeys(advice),  # dedupe, keep order
        )


@pytest.mark.check(
    id="workloads-postgres",
    title="PostgreSQL / TimescaleDB pods ready",
    section=SECTION,
)
@pytest.mark.kubernetes
def test_postgres_workloads():
    if not config.check_postgres:
        pytest.skip("external PostgreSQL configured (EXTERNAL_POSTGRES_HOST)")
    _check_namespace_workloads(
        "postgres",
        "PostgreSQL (StackGres)",
        "Install it with: helm upgrade --install stackgres charts/stackgres "
        "-n postgres --create-namespace -f environments/<name>/stackgres.values.yaml "
        "(the `data` phase). Also confirm the StackGres operator is running: "
        "kubectl get pods -n stackgres-system",
    )


@pytest.mark.check(
    id="workloads-mongodb", title="MongoDB pods ready", section=SECTION
)
@pytest.mark.kubernetes
def test_mongodb_workloads():
    if not config.check_mongodb:
        pytest.skip("external MongoDB configured (EXTERNAL_MONGO_HOST)")
    _check_namespace_workloads(
        "mongodb",
        "MongoDB",
        "Install it with: helm upgrade --install mongodb charts/mongodb -n mongodb "
        "--create-namespace -f environments/<name>/mongodb.values.yaml (the `data` phase).",
    )


@pytest.mark.check(
    id="workloads-rabbitmq", title="RabbitMQ pods ready", section=SECTION
)
@pytest.mark.kubernetes
def test_rabbitmq_workloads():
    if not config.check_rabbitmq:
        pytest.skip("external RabbitMQ configured (EXTERNAL_RABBITMQ_HOST)")
    _check_namespace_workloads(
        "rabbitmq",
        "RabbitMQ",
        "Install it with: helm upgrade --install rabbitmq charts/rabbitmq -n rabbitmq "
        "--create-namespace -f environments/<name>/rabbitmq.values.yaml (the `data` phase). "
        "Requires the RabbitMQ Cluster + Messaging Topology operators, installed while "
        "preparing the cluster.",
    )


@pytest.mark.check(id="workloads-minio", title="MinIO pods ready", section=SECTION)
@pytest.mark.kubernetes
def test_minio_workloads():
    if not config.check_minio:
        pytest.skip("external S3 storage configured (STORAGE_TYPE=s3)")
    _check_namespace_workloads(
        "minio",
        "MinIO",
        "Install it with: helm dependency update charts/minio && helm upgrade "
        "--install minio charts/minio -n minio --create-namespace "
        "-f environments/<name>/minio.values.yaml (the `data` phase).",
    )


@pytest.mark.check(
    id="workloads-platform",
    title="pid-gijon-core deployments ready",
    section=SECTION,
)
@pytest.mark.kubernetes
def test_platform_deployments():
    require("prereq-cluster")
    namespace = config.platform_namespace

    deployments = {
        item["metadata"]["name"]: item
        for item in kube.list_items("deployments", "-n", namespace)
    }
    if not deployments:
        fail(
            f"No deployments found in namespace '{namespace}'",
            "pid-gijon-core is not installed. Run the `core` phase: helm upgrade "
            "--install pid-gijon charts/pid-gijon-core -n pid-gijon --create-namespace "
            "-f environments/<name>/pid-gijon-core.values.yaml",
        )

    missing = [name for name in PLATFORM_DEPLOYMENTS if name not in deployments]
    unready = []
    for name in PLATFORM_DEPLOYMENTS:
        deployment = deployments.get(name)
        if deployment is None:
            continue
        status = deployment.get("status", {})
        desired = deployment.get("spec", {}).get("replicas", 1)
        ready = status.get("readyReplicas", 0)
        if ready < desired:
            unready.append(f"{name} ({ready}/{desired} ready)")

    problems = []
    advice = []
    if missing:
        problems.append("missing deployments: " + ", ".join(missing))
        if "web-back" in missing:
            advice.append(
                "web-back missing usually means the `webback` phase was not run yet: after the "
                "Keycloak setup, re-run helm upgrade WITHOUT "
                "--set components.webBack.enabled=false."
            )
        if [name for name in missing if name != "web-back"]:
            advice.append(
                "Other components missing: they may be disabled in your values "
                "(components.<name>.enabled) — re-check "
                "environments/<name>/pid-gijon-core.values.yaml."
            )
    if unready:
        problems.append("not ready: " + ", ".join(unready))
        advice.append(
            f"Inspect them: kubectl get pods -n {namespace} ; "
            f"kubectl logs -n {namespace} deploy/<name>"
        )

    pod_problems = _pod_problems(namespace)
    if pod_problems:
        problems.extend(f"{pod}: {problem}" for pod, problem, _ in pod_problems)
        advice.extend(dict.fromkeys(a for _, _, a in pod_problems))

    if problems:
        fail("pid-gijon-core is not fully up:\n" + "\n".join(problems), *advice)


@pytest.mark.check(
    id="workloads-keycloak-setup",
    title="Keycloak post-install values applied (no placeholders)",
    section=SECTION,
)
@pytest.mark.kubernetes
def test_keycloak_post_install_values_applied():
    require("prereq-cluster")
    secret = kube.get_json(
        "secret", "web-back-secret", "-n", config.platform_namespace
    )
    if secret is None:
        pytest.skip("web-back-secret not found (web-back not deployed yet)")

    placeholders = []
    for key, encoded in (secret.get("data") or {}).items():
        value = base64.b64decode(encoded).decode("utf-8", errors="replace")
        if "REPLACE_AFTER_KEYCLOAK_SETUP" in value:
            placeholders.append(key)

    if placeholders:
        fail(
            "web-back still runs with placeholder secrets: " + ", ".join(placeholders),
            "The one-time Keycloak setup was not completed (or not applied).",
            "Follow docs/06-post-install.md: copy the realm RS256 public key and the "
            "laravel-backend client secret into environments/<name>/"
            "pid-gijon-core.values.yaml, then re-run helm upgrade (the `webback` phase).",
            "Logins and all API checks below will fail until this is fixed.",
        )

    report.note("web-back secrets contain real Keycloak values (no placeholders).")
