#-------------------------------------------
# BASE — clean runtime image
#-------------------------------------------
FROM python:3.10-slim-bookworm AS base

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# The shared libraries are resolved as a local path dependency by `uv sync`,
# so they must be in place before it runs.
COPY --from=pylibs ./ /pylibs/

# Copy only manifests first — deps layer is cached until these change
COPY ./pyproject.toml ./uv.lock ./

RUN pip install --upgrade --no-cache-dir pip uv && \
    uv sync --locked --no-install-project --all-groups --no-cache

# Copy app code after deps — changes here won't invalidate the layer above
COPY ./ /code

# app/tmp is gitignored so COPY won't create it; ensure it exists at runtime
RUN mkdir -p app/tmp
# GDTIS-PT01-SEC-026 — ejecutar como usuario sin privilegios.
# UID/GID numericos (no nombre) para que el `runAsNonRoot` de Kubernetes pueda
# comprobarlo sin resolver /etc/passwd. Se coloca despues del ultimo COPY: todo
# lo anterior necesita root, y a partir de aqui el proceso ya no.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && chown -R 10001:10001 /code /opt/venv /pylibs
USER 10001:10001


#-------------------------------------------
# DEV
#-------------------------------------------
FROM base AS dev
CMD ["python3", "app/main.py"]

#-------------------------------------------
# PROD
#-------------------------------------------
FROM base AS prod
CMD ["python3", "app/main.py"]
