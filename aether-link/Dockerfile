FROM python:3.12-slim AS base

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Shared local libraries. They are resolved from disk ([tool.uv.sources] in
# pyproject.toml), so no package index credentials are needed to build.
COPY --from=pylibs ./ /pylibs/

# Copy only manifests — deps layer is cached until these change
COPY ./pyproject.toml ./uv.lock ./

RUN pip install --upgrade --no-cache-dir uv && \
    uv sync --locked --no-install-project --no-cache

# App code after deps — changes here won't invalidate the layer above
COPY ./ /code/

#----------------------------------#
# DEV
#----------------------------------#
FROM base AS dev

CMD ["gunicorn", "--config", "gunicorn/gunicorn.py", "app.main:app"]

#----------------------------------#
# PROD
#----------------------------------#
FROM base AS prod

CMD ["gunicorn", "--config", "gunicorn/gunicorn.py", "app.main:app"]
