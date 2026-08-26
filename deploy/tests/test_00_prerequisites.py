"""
Stage 0 — prerequisites.

Verifies the suite itself can run: configuration is present and the cluster is
reachable. Later stages depend on these checks and are skipped (not failed)
when a prerequisite is missing.
"""

import pytest

from helpers import kube, report
from helpers.config import config
from helpers.report import fail

SECTION = "Prerequisites"


@pytest.mark.check(
    id="prereq-config",
    title="Test configuration loaded (tests.env)",
    section=SECTION,
)
def test_configuration_present():
    missing = [
        name
        for name, value in (
            ("API_URL", config.api_url),
            ("FIWARE_MANAGER", config.fiware_manager_url),
            ("KEYCLOAK_URL", config.keycloak_url),
        )
        if not value
    ]
    if missing:
        fail(
            f"Missing required settings: {', '.join(missing)}",
            "Run the suite through tests/run-tests.sh <environment-name> so the "
            "generated environments/<name>/tests.env is loaded.",
            "If tests.env does not exist, re-run ./scripts/generate-env.sh <name> "
            "(it now renders tests.env alongside the Helm values).",
        )


@pytest.mark.check(
    id="prereq-cluster",
    title="Kubernetes cluster reachable (kubectl)",
    section=SECTION,
)
@pytest.mark.kubernetes
def test_cluster_reachable():
    reachable, reason = kube.cluster_reachable()
    if not reachable:
        context_hint = (
            f"KUBE_CONTEXT is set to '{config.kube_context}'"
            if config.kube_context
            else "KUBE_CONTEXT is empty, so the current kubectl context is used"
        )
        fail(
            f"Cannot talk to the cluster: {reason}",
            context_hint + " — set KUBE_CONTEXT in tests.env if that is wrong.",
            "Cluster-level diagnostics will be skipped; API checks still run.",
            "To run only the API checks intentionally: ./tests/run-tests.sh <env> "
            '-m "not kubernetes"',
        )
    report.note(
        "Cluster checks ran against context: "
        + (config.kube_context or "(current kubectl context)")
    )
