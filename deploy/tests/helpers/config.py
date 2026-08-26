"""
Test-suite configuration.

All settings come from environment variables, normally exported from the
generated environments/<name>/tests.env by tests/run-tests.sh. Every value has
a default so the suite degrades gracefully (checks that lack required settings
skip with an explanation instead of erroring).
"""

import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_bool(key: str, default: bool) -> bool:
    raw = _env(key)
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Config:
    """Settings for the platform verification suite."""

    # Public endpoints (from the generated environment)
    api_url: str = field(default_factory=lambda: _env("API_URL"))
    fiware_manager_url: str = field(default_factory=lambda: _env("FIWARE_MANAGER"))
    keycloak_url: str = field(default_factory=lambda: _env("KEYCLOAK_URL"))
    frontend_url: str = field(default_factory=lambda: _env("FRONTEND_URL"))
    keycloak_realm: str = field(default_factory=lambda: _env("KEYCLOAK_REALM", "pid-gijon"))

    # Platform credentials
    admin_username: str = field(default_factory=lambda: _env("ADMIN_USERNAME"))
    admin_password: str = field(default_factory=lambda: _env("ADMIN_PASSWORD"))

    # Device / data settings
    device_type: str = field(default_factory=lambda: _env("DEVICE_TYPE", "one_fiware"))
    # Serial de un dispositivo YA APROVISIONADO contra el que verificar el camino del
    # dato. La API de gestión ya no expone el alta de dispositivos, así que la batería
    # no puede crearse uno desechable: hay que indicárselo. Vacío = se saltan las
    # etapas 5 y 6.
    device_serial: str = field(default_factory=lambda: _env("TEST_DEVICE_SERIAL"))
    data_api_key: str = field(default_factory=lambda: _env("DATA_API_KEY"))
    tenant: str = field(default_factory=lambda: _env("TENANT"))

    # When true (default), a device data path that cannot be exercised because no
    # DATA_API_KEY could be resolved is a FAILURE, not a silent skip — otherwise a
    # broken/non-standard install would report green with the most important
    # checks quietly skipped. Set false to treat the data path as optional.
    require_data_path: bool = field(
        default_factory=lambda: _env_bool("REQUIRE_DATA_PATH", True)
    )

    # Async propagation polling (entity update via orion-ld, timeseries persist).
    # The platform is eventually consistent; these bound how long checks wait.
    propagation_attempts: int = field(
        default_factory=lambda: int(_env("PROPAGATION_ATTEMPTS", "8") or 8)
    )
    propagation_interval: float = field(
        default_factory=lambda: float(_env("PROPAGATION_INTERVAL_SECONDS", "2.5") or 2.5)
    )

    # HTTP behaviour
    tls_verify: bool = field(default_factory=lambda: _env_bool("TLS_VERIFY", False))
    http_timeout: int = field(default_factory=lambda: int(_env("HTTP_TIMEOUT", "15") or 15))

    # Kubernetes scope
    kube_context: str = field(default_factory=lambda: _env("KUBE_CONTEXT"))
    platform_namespace: str = field(default_factory=lambda: _env("PLATFORM_NAMESPACE", "pid-gijon"))

    # --- Airflow (optional; only checked when AIRFLOW_URL is set) -------------
    # Public URL of the Airflow 3 api-server and an admin login for its REST API.
    airflow_url: str = field(default_factory=lambda: _env("AIRFLOW_URL").rstrip("/"))
    airflow_username: str = field(default_factory=lambda: _env("AIRFLOW_USERNAME"))
    airflow_password: str = field(default_factory=lambda: _env("AIRFLOW_PASSWORD"))
    airflow_namespace: str = field(
        default_factory=lambda: _env("AIRFLOW_NAMESPACE", "airflow")
    )
    # Values written as Airflow Variables for the custom_iota_post test DAG and
    # used as its fallback defaults. apikey/tenant have no safe default, so the
    # check fails with guidance when they are missing.
    airflow_var_iota_url: str = field(
        default_factory=lambda: _env(
            "AIRFLOW_VAR_IOTA_URL"
        )
    )
    airflow_var_iota_apikey: str = field(
        default_factory=lambda: _env("AIRFLOW_VAR_IOTA_APIKEY")
    )
    airflow_var_datamodel: str = field(
        default_factory=lambda: _env("AIRFLOW_VAR_DATAMODEL", "Device")
    )
    airflow_var_tenant: str = field(default_factory=lambda: _env("AIRFLOW_VAR_TENANT"))
    airflow_var_scope: str = field(
        default_factory=lambda: _env("AIRFLOW_VAR_SCOPE", "/")
    )
    airflow_var_entity_name: str = field(
        default_factory=lambda: _env("AIRFLOW_VAR_ENTITY_NAME", "airflow-iota-test")
    )

    # Which bundled data services were deployed (false = external/managed)
    check_postgres: bool = field(default_factory=lambda: _env_bool("CHECK_POSTGRES", True))
    check_mongodb: bool = field(default_factory=lambda: _env_bool("CHECK_MONGODB", True))
    check_rabbitmq: bool = field(default_factory=lambda: _env_bool("CHECK_RABBITMQ", True))
    check_minio: bool = field(default_factory=lambda: _env_bool("CHECK_MINIO", True))


config = Config()
