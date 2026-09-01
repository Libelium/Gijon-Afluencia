FROM python:3.11.9-slim AS base

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Pull the distro's patched OpenSSL/libssl3 — fixes CVE-2025-15467 and the
# rest of the Jan-2026 OpenSSL batch flagged against this image (was 3.0.14).
# Debian backports the fix into the package revision, so the authoritative
# check is `dpkg -l libssl3`, not the `openssl version` string.
RUN apt-get update \
 && apt-get install -y --only-upgrade openssl libssl3 \
 && rm -rf /var/lib/apt/lists/*

# Copy only manifests — deps layer is cached until these change
COPY ./pyproject.toml ./uv.lock ./

RUN pip install --upgrade --no-cache-dir uv && \
    uv sync --locked --no-install-project --all-groups --no-cache

# App code after deps — changes here won't invalidate the layer above
COPY ./ /code/
# GDTIS-PT01-SEC-026 — ejecutar como usuario sin privilegios.
# UID/GID numericos (no nombre) para que el `runAsNonRoot` de Kubernetes pueda
# comprobarlo sin resolver /etc/passwd. Se coloca despues del ultimo COPY: todo
# lo anterior necesita root, y a partir de aqui el proceso ya no.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && chown -R 10001:10001 /code /opt/venv
USER 10001:10001


#----------------------------------#
# DEV
#----------------------------------#
FROM base AS dev

CMD ["gunicorn", "--config", "config/gunicorn.py", "app.main:app"]


#----------------------------------#
# PROD
#----------------------------------#
FROM base AS prod

CMD ["gunicorn", "--config", "config/gunicorn.py", "app.main:app"]
