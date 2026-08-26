"""
The CronJob of the anomaly vertical: sweep a storage folder, score whatever CSVs
are waiting there, leave them scored in `processed/`.

    anomalies_detection/{tenant}/{scope}/*.csv          dropped here to be scored
    anomalies_detection/{tenant}/{scope}/models/        one bundle per datamodel
    anomalies_detection/{tenant}/{scope}/processed/     the same rows + isOutlier

NOT an ETL in three phases, on purpose: there is no extraction (somebody leaves a
file), and the load is writing that same file back with one more column. Splitting
it into extract/transform/load would be ceremony over ~100 lines.

INPUT FORMAT: the platform IMPORT csv (wide), `timestamp,urn,type,<one column per
measure>`. Not the export (long) one, and the reason is not taste: a row of the wide
csv IS a point - every measure of one entity at one instant, which is exactly what
the model needs. The long format would have to be pivoted first, and its single
`value` column mixes every measure's type, so one text measure makes the whole
column text. Wide keeps that contamination per measure, which is the granularity
worth having. Convert an export first.

Empty folder -> does nothing and says so. That is the normal state most runs.
"""

import logging
import os
import tempfile

import pandas as pd

from crowd_predictions.anomaly_detection import storage as anomaly_storage
from crowd_predictions.anomaly_detection.core import evaluate_batch
from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.helpers.fiware_targets import run_for_each_target

logger = logging.getLogger(__name__)

# Columns the import format reserves. Everything else is a candidate measure.
RESERVED_COLUMNS = ("timestamp", "urn", "type", "tenant", "scope")
OUTLIER_COLUMN = "isOutlier"
# A real platform export is SPARSE: coverage varies widely between columns, because the
# platform does not report every attribute at every instant. A point needs ALL its
# measures at the same instant, so auto-detecting every numeric column and demanding
# all of them scored zero rows on the first export tried. The threshold itself is
# per datamodel (ANOMALY_CONFIG['<datamodel>']['min_measure_coverage']).


def pending_csv_keys(storage) -> list:
    """The CSVs waiting at the root of this tenant/scope's folder, sorted.

    Only the root: `models/` and `processed/` live underneath and must never be
    picked up as input - re-scoring our own output would teach the model its own
    verdicts."""
    root = anomaly_storage.anomaly_key("")
    keys = storage.list_prefix(root) or []
    return sorted(k for k in keys
                  if k.lower().endswith(".csv") and "/" not in k[len(root):].strip("/"))


def read_wide_csv(storage, key: str, local_dir: str) -> pd.DataFrame:
    """Download and parse one import-format csv. `timestamp` is parsed to naive UTC,
    the convention every module here works in."""
    local_path = os.path.join(local_dir, os.path.basename(key))
    storage.download_file(key, local_path)
    df = pd.read_csv(local_path)

    missing = [c for c in ("timestamp", "urn", "type") if c not in df.columns]
    if missing:
        raise ValueError(f"'{key}' is not an import-format csv: missing {missing}. "
                         "Expected timestamp,urn,type,<measures> - convert an export "
                         "csv first.")

    stamps = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="mixed")
    df["timestamp"] = stamps.dt.tz_convert("UTC").dt.tz_localize(None)
    unparseable = int(df["timestamp"].isna().sum())
    if unparseable:
        logger.warning(f"'{key}': {unparseable} row(s) with an unreadable timestamp, dropped.")
        df = df[df["timestamp"].notna()]
    return df


def datamodel_of(df: pd.DataFrame, key: str) -> str:
    """The `type` column, which is authoritative - not the file name. A file mixing
    datamodels is rejected: one model per datamodel means mixing them would train a
    single model on two different signals."""
    types = sorted(df["type"].dropna().unique())
    if len(types) != 1:
        raise ValueError(f"'{key}' carries {len(types)} datamodels ({types[:5]}). "
                         "One file per datamodel: split it before dropping it here.")
    return str(types[0])


def numeric_measures(df: pd.DataFrame, key: str,
                     min_coverage: float = settings.DEFAULT_ANOMALY_MIN_MEASURE_COVERAGE) -> list:
    """Measure columns that are usable as dimensions, in stable (sorted) order.

    Coerced PER COLUMN, which is the whole reason for wanting the wide format: a
    text or JSON measure only disqualifies itself. A column is kept when:

      - every non-empty cell is numeric - one stray string means it is not a
        number series, and half-reading it would invent points;
      - it is present in at least `min_coverage` of the rows: a sparse column
        makes every row that lacks it unscorable;
      - it actually varies. A column with one distinct value carries no
        information (its z-score is 0 for ever) and is usually an id or a
        constant of the deployment - `serialNumber` was auto-detected as a
        measure on a real export."""
    candidates = [c for c in df.columns if c not in RESERVED_COLUMNS]
    kept, dropped = [], []
    for column in candidates:
        values = df[column].dropna()
        if values.empty:
            dropped.append(f"{column} (empty)")
            continue
        coerced = pd.to_numeric(values, errors="coerce")
        if coerced.isna().any():
            dropped.append(f"{column} (not numeric)")
            continue
        coverage = len(values) / len(df)
        if coverage < min_coverage:
            dropped.append(f"{column} ({coverage:.0%} coverage)")
            continue
        if coerced.nunique() <= 1:
            dropped.append(f"{column} (constant)")
            continue
        df[column] = pd.to_numeric(df[column], errors="coerce")
        kept.append(column)

    if dropped:
        logger.info(f"'{key}': {len(dropped)} column(s) not usable as measures: {dropped}")
    return sorted(kept)


def points_from(df: pd.DataFrame, measure_names: list, key: str) -> list:
    """One point per row: every configured measure of one entity at one instant.

    A row missing any of them is SKIPPED, never filled in: a forward-filled
    dimension has delta 0 and rolling_std 0, which is precisely the signature of a
    frozen sensor - we would be manufacturing the anomaly we are looking for."""
    usable = df.dropna(subset=measure_names)
    skipped = len(df) - len(usable)
    if skipped:
        logger.warning(f"'{key}': {skipped} row(s) missing at least one configured "
                       "measure, skipped rather than filled in.")
    return [{"entity_id": row["urn"],
             "raw_measures": {m: row[m] for m in measure_names},
             "timestamp": row["timestamp"].to_pydatetime()}
            for _, row in usable.iterrows()]


def measure_names_for(storage, datamodel: str, df: pd.DataFrame, key: str) -> list:
    """The measures to score this datamodel on: whatever ANOMALY_CONFIG declares,
    or - when it declares none - every numeric column, auto-detected.

    Auto-detection is FROZEN by the first run: the stored model's own columns
    sidecar already holds the set, and a later file that happens to carry one column
    fewer must not silently redefine the vector. It would not degrade the model, it
    would RESET it - and with one model per datamodel that is every entity's history
    at once."""
    configured = settings.anomaly().measures_for(datamodel)
    if configured:
        return configured

    detected = numeric_measures(df, key,
                                settings.anomaly().min_measure_coverage_for(datamodel))
    frozen = anomaly_storage.stored_measure_names(storage, datamodel)
    if not frozen:
        logger.info(f"'{datamodel}': no measures configured, auto-detected {detected} "
                    "and frozen for this model from now on.")
        return detected

    missing = [m for m in frozen if m not in detected]
    if missing:
        logger.warning(f"'{datamodel}': the stored model was built on {frozen} and this "
                       f"file is missing {missing}. Keeping the stored set - rows without "
                       "those measures are skipped, the model is NOT reset.")
    extra = [m for m in detected if m not in frozen]
    if extra:
        logger.info(f"'{datamodel}': ignoring column(s) {extra}, not part of the model's "
                    "frozen measure set.")
    return frozen


def process_csv(storage, key: str, local_dir: str) -> int:
    """Score one file and leave it in `processed/`. Returns rows scored."""
    df = read_wide_csv(storage, key, local_dir)
    if df.empty:
        logger.warning(f"'{key}': no usable rows, moved aside without scoring.")
        _archive(storage, key, df, local_dir)
        return 0

    datamodel = datamodel_of(df, key)
    measure_names = measure_names_for(storage, datamodel, df, key)
    if not measure_names:
        raise ValueError(f"'{key}': no numeric measure to score {datamodel} on.")

    missing = [m for m in measure_names if m not in df.columns]
    points = points_from(df, [m for m in measure_names if m in df.columns], key) if not missing \
        else []
    if missing:
        logger.warning(f"'{key}': missing column(s) {missing} of the model's measure set - "
                       "nothing scored from this file.")

    verdicts = evaluate_batch(storage, datamodel, points, measure_names) if points else {}
    df[OUTLIER_COLUMN] = [
        verdicts.get((row["urn"], row["timestamp"].to_pydatetime()), {}).get(OUTLIER_COLUMN)
        for _, row in df.iterrows()
    ]
    _archive(storage, key, df, local_dir)

    scored = int(df[OUTLIER_COLUMN].notna().sum())
    flagged = int((df[OUTLIER_COLUMN] == 1).sum())
    logger.info(f"'{key}': {scored}/{len(df)} row(s) scored for {datamodel}, {flagged} flagged.")
    return scored


def _archive(storage, key: str, df: pd.DataFrame, local_dir: str) -> None:
    """Write the scored csv under `processed/` and drop the original.

    Moved and not left in place: this job is a CronJob, and a file that stays gets
    re-read on every run for ever. The watermark inside the model keeps that from
    re-training on the same points, but it would still re-score and re-publish
    them."""
    name = os.path.basename(key)
    out_path = os.path.join(local_dir, f"processed_{name}")
    df.to_csv(out_path, index=False)
    storage.upload_file(anomaly_storage.anomaly_key("processed", name), out_path)
    storage.delete_file(key)


def run_one(tenant: str, scope: str) -> int:
    """One sweep for one tenant/scope. 0 even with nothing to do: an empty folder is
    the normal state of most runs, not a failure."""
    storage = get_storage()
    keys = pending_csv_keys(storage)
    if not keys:
        logger.info(f"{tenant}/{scope}: nothing waiting in "
                    f"{anomaly_storage.anomaly_key('')} - nothing to do.")
        return 0

    logger.info(f"{tenant}/{scope}: {len(keys)} file(s) to score")
    failed = 0
    with tempfile.TemporaryDirectory() as local_dir:
        for key in keys:
            try:
                process_csv(storage, key, local_dir)
            except Exception as e:
                # Per file: one malformed csv must not stop the others, and it stays
                # where it is so it can be fixed and picked up on the next run.
                failed += 1
                logger.exception(f"'{key}' could not be processed and was left in place: {e}")
    return 1 if failed else 0


def main() -> int:
    """One sweep per FIWARE_TARGETS entry. A failing target does not abort the
    others but does turn the exit code red (see run_for_each_target)."""
    return run_for_each_target(run_one, logger)
