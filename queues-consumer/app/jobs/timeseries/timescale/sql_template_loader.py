"""
This module is a singleton for SQL templates.
Because every job that needs to execute some SQL, it
is better to have a single instance of the template loader,
with the loaded templates, so we don't have to load the
templates every time a job is executed.

SEC-020
-------
`check_schema.sql.jinja` interpolates a schema name derived from the `tenant`
field of an NGSI-LD notification - attacker-influenced input - into
`CREATE SCHEMA`, `CREATE TABLE`, `to_regclass('...')` and friends, and the
result is handed to SQLAlchemy's `text()` and executed. Rendering it with an
unvalidated value is a SQL injection with DDL privileges.

A note on the remedy, because it differs from "turn Jinja autoescape on":
autoescape is *HTML* escaping. It would rewrite `&`, `<`, `>` and quotes into
character entities, which corrupts SQL without preventing injection - a payload
made of only `[A-Za-z0-9_; -]` passes through it untouched. The protection that
actually works here is a strict allow list on the identifier plus proper
identifier quoting, which is what `render_check_schema` does. `autoescape` is
still pinned to False explicitly so the choice is visible rather than implied by
the default.
"""

import pathlib
import re

import jinja2

# The loader used to point at the absolute container path
# "/code/app/jobs/timeseries/timescale/sql_templates/", so importing this module
# anywhere but inside the image raised TemplateNotFound. Resolve it relative to
# this file instead.
_TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent / "sql_templates"

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,  # SQL, not markup - see the module docstring (SEC-020)
)

check_schema_template = jinja_env.get_template("check_schema.sql.jinja")


# Lowercase letters, digits and underscores only: exactly what an unquoted
# PostgreSQL identifier may hold without folding or escaping surprises, and
# narrow enough that no separator, quote, semicolon or comment marker survives.
_SCHEMA_NAME_RE = re.compile(r"^[a-z0-9_]+$")

# PostgreSQL truncates identifiers at NAMEDATALEN-1 = 63 bytes. Rejecting rather
# than truncating avoids two tenants collapsing onto the same schema.
_MAX_IDENTIFIER_LENGTH = 63


class InvalidSchemaName(ValueError):
    """Raised when a schema name would not be safe to interpolate into SQL."""


def validate_schema_name(schema: str) -> str:
    """
    Return `schema` unchanged if it is a safe bare SQL identifier, otherwise
    raise InvalidSchemaName.
    """
    if not isinstance(schema, str) or not _SCHEMA_NAME_RE.match(schema):
        raise InvalidSchemaName(
            f"Refusing to build SQL for schema name {schema!r}: "
            "only [a-z0-9_] is allowed"
        )

    if len(schema.encode("utf-8")) > _MAX_IDENTIFIER_LENGTH:
        raise InvalidSchemaName(
            f"Refusing to build SQL for schema name {schema!r}: "
            f"longer than {_MAX_IDENTIFIER_LENGTH} bytes"
        )

    return schema


def quote_identifier(name: str) -> str:
    """
    Quote a validated identifier the way PostgreSQL expects.

    Doubling embedded double quotes is redundant after `validate_schema_name`,
    but it keeps this function correct on its own terms if it is ever reused.
    """
    return '"' + name.replace('"', '""') + '"'


def render_check_schema(schema: str) -> str:
    """
    Render the schema bootstrap script for `schema`.

    The template receives the name twice on purpose: `schema` for the positions
    where it appears inside a SQL string literal (`schema_name = '...'`,
    `to_regclass('...')`) and `schema_ident` for the positions where it is a
    real identifier (`CREATE SCHEMA ...`).
    """
    validate_schema_name(schema)

    return check_schema_template.render(
        schema=schema,
        schema_ident=quote_identifier(schema),
    )
