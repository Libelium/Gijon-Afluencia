"""
Database-side timeseries hashing for the Platform Timescale backend.

Computes a deterministic sha256 digest of the canonical row representation
directly inside Postgres via the pgcrypto extension. Only the 64-char hex
digest crosses the network — raw rows never leave the DB.

Requires `CREATE EXTENSION IF NOT EXISTS pgcrypto;` on the platform timescale DB
(idempotent; safe to run repeatedly).
"""

import re
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

import app.core.time_series.data_sources.timescale.constants as ts_constants


# Allow only safe characters in tenant names since the value is interpolated
# into the SQL query as a schema identifier (Postgres bindparams do not work
# for identifiers).
_SAFE_TENANT = re.compile(r"^[A-Za-z0-9_]+$")


def _build_hash_sql(schema: str) -> text:
    # U&'\001f' = ASCII unit separator, U&'\001e' = ASCII record separator.
    # Both are control characters that cannot appear in legitimate field
    # values, so the canonical string is unambiguous and the hash is
    # collision-resistant against adversarial values that try to mimic
    # delimiter characters. ORDER BY inside string_agg is critical for
    # determinism.
    return text(f"""
        SELECT
            encode(
                digest(
                    COALESCE(
                        string_agg(
                            entity_id || U&'\\001f' ||
                            attr_id || U&'\\001f' ||
                            extract(epoch from "time")::text || U&'\\001f' ||
                            COALESCE(
                                attr_double_value::text,
                                attr_string_value,
                                attr_boolean_value::text,
                                attr_json_value::text,
                                ''
                            ),
                            U&'\\001e' ORDER BY entity_id, attr_id, "time"
                        ),
                        ''
                    ),
                    'sha256'
                ),
                'hex'
            ) AS data_hash,
            COUNT(*) AS row_count
        FROM "{schema}"."entity_data"
        WHERE scope_id = :scope_id
          AND (CAST(:has_devices  AS bool) IS FALSE OR entity_id = ANY(:entity_ids))
          AND (CAST(:has_measures AS bool) IS FALSE OR attr_id   = ANY(:attr_ids))
          AND (CAST(:start_date AS timestamptz) IS NULL OR "time" >= CAST(:start_date AS timestamptz))
          AND (CAST(:end_date   AS timestamptz) IS NULL OR "time" <= CAST(:end_date   AS timestamptz))
    """)


def execute_hash_query(
    session: Session,
    tenant: str,
    scope: str,
    entity_ids: List[str],
    attr_ids: List[str],
    start_date,
    end_date,
) -> Tuple[str, int]:
    """
    Execute the hash aggregation and return (data_hash, row_count).
    """
    if not _SAFE_TENANT.match(tenant or ""):
        raise ValueError(
            f"Invalid tenant identifier for hash query: {tenant!r}"
        )

    schema = f"{ts_constants.SCHEMA_PREFIX}{tenant}"
    stmt = _build_hash_sql(schema)

    row = session.execute(
        stmt,
        {
            "scope_id": scope,
            "has_devices": bool(entity_ids),
            "entity_ids": list(entity_ids or []),
            "has_measures": bool(attr_ids),
            "attr_ids": list(attr_ids or []),
            "start_date": start_date,
            "end_date": end_date,
        },
    ).one()

    return row.data_hash or "", int(row.row_count)
