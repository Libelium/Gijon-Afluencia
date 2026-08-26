FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Force HTTPS on the apt repos
RUN find /etc/apt/sources.list.d/ -type f -print0 | xargs -0 sed -i 's/http:/https:/g'

# libgomp1: xgboost needs it at runtime (libgomp.so.1) and python:3.10-slim does
# not ship it. It is the ONLY system package needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e ".[test]" && \
    # AFTER the install, never before: pip re-resolves xgboost's dependencies and
    # would put it straight back. xgboost pulls nvidia-nccl-cu12 (~300MB) for
    # multi-GPU/dask and we train on CPU - dropping it saves 300MB per image pull.
    pip uninstall -y nvidia-nccl-cu12

RUN chmod +x scripts/main.py scripts/train.py scripts/predict.py

# Default CMD: LIDAR+SmartSpot fusion. The two CronJobs override the command on
# this SAME image with "python scripts/run_daily.py" (train + predict) and
# "python scripts/run_ote.py" (compact + ingest the LIDAR archive) - see
# deploy/README.md. train.py and predict.py stay runnable on their own.
CMD ["python", "scripts/main.py"]
