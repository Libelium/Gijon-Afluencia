"""
Metrics for the EntitySync job — entity ingestion tracking per tenant.

Designed for operational monitoring and future billing attribution.
All metrics are labelled by ``tenant`` (maps to a billing client),
so per-client usage is immediately queryable.

Metrics exposed
---------------
entity_sync_entities_total
    Counter — one increment per entity notification received.
    Primary billing unit: "how many entities did tenant X send?"

entity_sync_attributes_total
    Counter — incremented by the number of attributes in each notification.
    Data-volume proxy: a client sending 1 entity with 1 000 attributes
    contributes far more than one sending 1 000 entities with 1 attribute,
    and this metric captures that difference.

entity_sync_payload_bytes_total
    Counter — incremented by the byte size of the serialised entity payload
    (measured right after protocol translation, before any DB enrichment).
    Secondary billing signal: captures both attribute count *and* value size,
    giving a more accurate picture of raw data volume than attribute count alone.
"""

from config.logging import appLogging as logging
from metrics.collectors.base import Collector
from metrics.registry import counter

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

entities_total = counter(
    "entity_sync_entities_total",
    "Total entity notifications received by EntitySync, labelled by tenant.",
    ["tenant"],
)

attributes_total = counter(
    "entity_sync_attributes_total",
    "Total attributes received across all EntitySync entity notifications. "
    "Use as a data-volume proxy: a notification with many attributes "
    "contributes proportionally more than one with few.",
    ["tenant"],
)

payload_bytes_total = counter(
    "entity_sync_payload_bytes_total",
    "Total bytes of serialised entity payloads processed by EntitySync "
    "(measured on the translated notification, before DB enrichment). "
    "Combines attribute count and value size into a single data-volume signal.",
    ["tenant"],
)


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class SyncMetricsCollector(Collector):
    """
    Collector for EntitySync ingestion metrics.

    Unlike task-level collectors, this one does not rely on Celery signals:
    EntitySync calls ``record_entity()`` directly after translating each entity,
    which is the earliest point at which tenant, type, and payload data are
    all available.
    """

    def register(self) -> None:
        # No Celery signals needed; metrics are pushed via record_entity().
        pass

    @staticmethod
    def record_entity(
        tenant: str,
        attribute_count: int,
        payload_bytes: int,
    ) -> None:
        """
        Record one processed entity notification.

        Call this right after protocol translation, before any DB enrichment,
        so the payload size reflects the raw incoming data volume.

        Parameters
        ----------
        tenant:
            Tenant identifier — maps directly to a billing client.
        attribute_count:
            Number of attributes present in the entity notification.
        payload_bytes:
            Byte length of the serialised entity payload (UTF-8 JSON).
        """
        try:
            labels = {"tenant": tenant}
            entities_total.labels(**labels).inc()
            attributes_total.labels(**labels).inc(attribute_count)
            payload_bytes_total.labels(**labels).inc(payload_bytes)
        except Exception as e:
            logging.error(f"[metrics] record_entity failed: {e}", exc_info=True)
