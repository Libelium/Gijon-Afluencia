"""
Several tenant/scope pairs in one run: FIWARE_TARGETS=tenant_a:/,tenant_b:/

With an optional third field, the LIDAR devices of that target:
FIWARE_TARGETS=tenant_a:/:L1|L2,tenant_b:/:L3 - needed because the raw LIDAR feed
carries no tenant, only the device id of the URL it was posted to.

The pair goes TOGETHER in each item, not as two parallel lists: with
FIWARE_TENANTS=a,b + FIWARE_SCOPES=/,/ one extra element crosses a tenant with
another's scope, and this platform does not report that - the time-series
endpoint answers HTTP 200 with an empty "time_series".

The pair travels downwards as a TEMPORARY MUTATION of os.environ, chosen over
threading it through half a dozen signatures: the three consumers
(helpers/aether.py, helpers/model_storage.py, helpers/uploader.py) all reach the
values through config/settings.py, which reads os.environ on every call, so
nothing else has to change. Not thread/async safe - one target at a time, which is
what the CronJob does.

⚠️ This whole mechanism rests on nothing caching FIWARE_TENANT/FIWARE_SCOPE. A
cached tenant makes every target read the first one's, with no error anywhere.
"""

import contextlib
import logging
import os

from crowd_predictions.config import settings
from crowd_predictions.helpers.model_storage import tenant_scope

logger = logging.getLogger(__name__)

DEFAULT_SCOPE = "/"
# OTE_DEVICE_IDS travels with the pair because the LIDAR raw feed carries NO tenant:
# fiware-manager only knows the device id of the URL, so without saying which devices
# belong to each target, every target would publish every device's data.
_ENV_KEYS = ("FIWARE_TENANT", "FIWARE_SCOPE", "OTE_DEVICE_IDS")
# Separates the device ids of one target: "," already separates targets and ":" the
# fields.
DEVICE_SEPARATOR = "|"


class NoTargetError(RuntimeError):
    """There is no tenant to work for.

    Its own type so the entry points can turn it into a single clear line, the same
    as AetherConfigError.
    """


def parse_target_specs(raw: str = None) -> list:
    """
    [(tenant, scope, device_ids)] from FIWARE_TARGETS=tenant:scope:dev1|dev2

    The third field is OPTIONAL and only the LIDAR ingestion uses it; `None` there
    means "every device", which is what every target had before it existed. It lives
    here and not in its own variable so the devices cannot drift from the target they
    belong to - the same reason the pair travels together (see the module docstring).

    A tenant with no ":" (or with an empty one) gets scope "/". A repeated tenant/scope is
    one target, not two - it would train it twice and upload the second model over the
    first - but its device ids are MERGED.

    An EMPTY tenant raises instead of becoming a target. It used to be accepted, and
    everything downstream worked: the CSVs were generated, the queue answered 200 and
    the run ended green - but the consumer drops any notification whose tenant is
    empty (crud_entity.get_or_create_entity), so NOTHING was ever created. A missing
    ConfigMap entry looked exactly like a healthy deployment.
    """
    raw = settings.fiware().FIWARE_TARGETS if raw is None else raw

    by_pair = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        tenant, separator, rest = chunk.partition(":")
        tenant = tenant.strip()
        if not tenant:
            continue
        scope, _devices_separator, devices = rest.partition(":")
        scope = scope.strip() if separator else DEFAULT_SCOPE
        pair = (tenant, scope or DEFAULT_SCOPE)
        # The repeated pair is not a second target, but its devices are ADDED instead of
        # dropped: "tenant_a:/:L1,tenant_a:/:L2" is the natural way to try to add a sensor, and
        # keeping only L1 would leave L2 unpublished with nothing saying so.
        if pair in by_pair:
            logger.warning(f"{target_label(*pair)} appears more than once in "
                           "FIWARE_TARGETS: its device ids are merged, not duplicated")
        merged = by_pair.setdefault(pair, [])
        merged.extend(device for device in (_device_ids(devices) or ())
                      if device not in merged)

    if by_pair:
        return [(tenant, scope, tuple(devices) or None)
                for (tenant, scope), devices in by_pair.items()]

    fiware = settings.fiware()
    if not fiware.FIWARE_TENANT.strip():
        raise NoTargetError(
            "No tenant to work for: FIWARE_TARGETS is empty and FIWARE_TENANT is not set. "
            "Nothing is done - publishing with an empty tenant creates no entity in the platform "
            "and the run would still look successful."
        )
    return [(fiware.FIWARE_TENANT, fiware.FIWARE_SCOPE or DEFAULT_SCOPE, None)]


def _device_ids(raw: str):
    """"L1|L2" -> ("L1", "L2"). Empty means unset, not "no device": a target with an
    empty list would publish nothing and look healthy."""
    ids = tuple(part.strip() for part in raw.split(DEVICE_SEPARATOR) if part.strip())
    return ids or None


def target_label(tenant: str, scope: str) -> str:
    """Prefix for the logs, in the same "tenant:scope" shape as FIWARE_TARGETS.
    Without it, an "MAE=12.3" with several targets does not say whose it is."""
    return f"[{tenant}:{scope}]"


def target_slug(tenant: str = None, scope: str = None) -> str:
    """Filesystem-safe "tenant_scope". Same normalization - and the same refusal to
    invent a tenant - as helpers/model_storage.tenant_scope()."""
    if tenant is None or scope is None:
        active_tenant, active_scope = tenant_scope()
        return f"{tenant or active_tenant}_" \
               f"{(scope.strip('/').replace('/', '_') or '_') if scope is not None else active_scope}"
    return f"{tenant}_{scope.strip('/').replace('/', '_') or '_'}"


class _TargetPrefixFilter(logging.Filter):
    """Prefixes every record with the target. Attached to the root HANDLERS (not
    the logger) so it also catches what aether.py/uploader.py log; the flag stops
    a second handler from prefixing twice."""

    def __init__(self, label: str):
        super().__init__()
        self.label = label

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "_fiware_target_prefixed", False):
            record.msg = f"{self.label} {record.getMessage()}"
            record.args = ()
            record._fiware_target_prefixed = True
        return True


@contextlib.contextmanager
def fiware_target(tenant: str, scope: str, device_ids=None):
    """
    Pins FIWARE_TENANT/FIWARE_SCOPE (and the log prefix) for the block, and
    restores the previous values on exit, exceptions included.

    `device_ids` also pins OTE_DEVICE_IDS, which the LIDAR extract already reads: that
    way the devices of a target reach it with no extra plumbing. Not given leaves
    whatever was set globally, so a single-tenant deployment keeps working.
    """
    previous = {key: os.environ.get(key) for key in _ENV_KEYS}
    os.environ["FIWARE_TENANT"] = tenant
    os.environ["FIWARE_SCOPE"] = scope
    if device_ids:
        os.environ["OTE_DEVICE_IDS"] = ",".join(device_ids)

    log_filter = _TargetPrefixFilter(target_label(tenant, scope))
    handlers = list(logging.getLogger().handlers)
    for handler in handlers:
        handler.addFilter(log_filter)

    try:
        yield (tenant, scope)
    finally:
        for handler in handlers:
            handler.removeFilter(log_filter)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_for_each_target(run_one, logger: logging.Logger, config_errors: tuple = ()) -> int:
    """
    Runs run_one(tenant, scope) -> int once per target, isolating the failures:
    one tenant with no data must not abort the rest.

    Returns 0 only if EVERY target succeeded. "Any" and not "all" on purpose:
    this is a CronJob, and a target going days without being trained while the
    job stays green is worse than a job in red.

    config_errors are logged as a single line (somebody has to fix configuration
    or ingest data); anything else keeps its traceback because it is a bug here.

    No tenant at all is caught HERE rather than left to each entry point: it is not a
    failure of one target, it is having nothing to do, and it has to be red.
    """
    try:
        targets = parse_target_specs()
    except NoTargetError as e:
        logger.error(f"NOTHING TO DO: {e}")
        return 1

    logger.info(f"{len(targets)} target(s): "
                f"{', '.join(target_label(t, s) for t, s, _d in targets)}")

    failed = []
    for tenant, scope, device_ids in targets:
        label = target_label(tenant, scope)
        try:
            with fiware_target(tenant, scope, device_ids):
                exit_code = run_one(tenant, scope)
            if exit_code != 0:
                failed.append(label)
        except config_errors as e:
            logger.error(f"{label} FAILED: {e}")
            failed.append(label)
        except Exception:
            logger.exception(f"{label} FAILED with an unexpected error")
            failed.append(label)

    ok = len(targets) - len(failed)
    logger.info(f"SUMMARY: {ok}/{len(targets)} targets OK")
    if failed:
        logger.error(f"Failed targets: {', '.join(failed)}")
        return 1
    return 0
