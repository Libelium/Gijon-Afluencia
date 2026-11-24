import ast
import json
import pandas as pd
import dateutil.parser
from config.logging import appLogging as logging

# The Smart Spot sends the block as r_cfe_block. Provisioning applies no datamodel mapping, so
# it reaches the broker and Timescale under that name instead of cfeBlock: request and accept both.
CFE_BLOCK_MEASURES = ["cfeBlock", "r_cfe_block"]

CFE_BLOCK_PREFIX = "r_cfe_"

# Older cache files wrote the Smart Spot cfeBlock rows (newer firmware) with
# lowercase names and the loose-attribute rows (older firmware) in camelCase,
# sometimes both in the same file. Readers fold them onto the camelCase name.
CROWD_LEGACY_COLUMN_ALIASES = {
    "entityid": "entityId",
    "israndommac": "random",
    "visitorid": "visitorId",
    "detectiontype": "detectionType",
    "visitortype": "visitorType",
}

# Fixed layout of the hourly CSVs written to data_cache/crowd. Same columns,
# names and types whatever the firmware that produced the detection.
CROWD_CACHE_SCHEMA_VERSION = 2
CROWD_CACHE_INT_COLUMNS = ["detectionType", "random", "rssi", "period"]
CROWD_CACHE_COLUMNS = [
    "timeinstant",
    "entityId",
    "detectionType",
    "random",
    "visitorId",
    "rssi",
    "ssid",
    "signature",
    "fields",
    "period",
    "schemaVersion",
]
CROWD_CACHE_TIMEINSTANT_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
# What identifies one reported row. The same visitor shows up in many reports,
# so a visitor's repeats are real rows: only the full set of reported values
# tells a row apart. fields is left out because files cached before schema 2
# never had it.
CROWD_CACHE_ROW_KEYS = [
    c for c in CROWD_CACHE_COLUMNS if c not in ("fields", "schemaVersion")
]


def append_new_crowd_rows(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """
    Appends to an hour already cached the rows of a new read that it does not
    have yet. Repeats inside each side are kept as they are (they are real
    reports); a row of the new read that the cached file already holds is not
    added again, so re-running an hour is idempotent.
    """
    if existing.empty:
        return new
    # NaN (read back from a CSV) and pd.NA (built in memory) must compare equal
    keys_of = lambda df: (
        df[CROWD_CACHE_ROW_KEYS].astype("string").fillna("").agg("\x1f".join, axis=1)
    )
    already = set(keys_of(existing))
    fresh = new[~keys_of(new).isin(already)] if not new.empty else new
    merged = pd.concat([existing, fresh], ignore_index=True)
    return merged.sort_values("timeinstant", kind="stable").reset_index(drop=True)


def _parse_cfe_block(value):
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return ast.literal_eval(value)


def _to_json_if_nested(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"))
    return value


def crowd_row_processing_lambda(df, measures_renames = None, keep_unmapped_fields = False):
    """
    Flattens the Smart Spot cfeBlock (newer firmware) so that each detection in
    the block becomes one row, like the loose-attribute rows of the older firmware.
    The block arrives as a list of detections or, with a single one, as a dict.

    With keep_unmapped_fields, block keys without an entry in measures_renames
    (e.g. r_cfe_fields) are kept as columns named without the r_cfe_ prefix, and
    list/dict values are serialised as JSON. Only the data cache uses it: the
    advanced crowd ETLs drop rows with any NaN, so extra columns would cost rows.
    """

    # Nothing to process
    if df.empty:
        return df

    if "r_cfe_block" in df.columns:
        raw_block = df.pop("r_cfe_block")
        df["cfeBlock"] = df["cfeBlock"].combine_first(raw_block) if "cfeBlock" in df.columns else raw_block

    if "cfeBlock" not in df.columns:
        if "timeinstant" in df.columns:
            df["timeinstant"] = pd.to_datetime(df["timeinstant"], format="mixed")
        return df

    # Rows with a real cfeBlock value (not null or empty string)
    mask_has_cfe = df["cfeBlock"].notna() & (df["cfeBlock"] != "")

    # Column exists but is empty for all rows: drop it to avoid polluting the
    # result schema with empty CFE columns
    if not mask_has_cfe.any():
        df = df.drop(columns=["cfeBlock"])
        df["timeinstant"] = pd.to_datetime(df["timeinstant"], format="mixed")
        return df

    if measures_renames is None:
        measures_renames = {
            "r_cfe_random": "random",
            "r_cfe_visitorId": "visitorId",
            "r_cfe_detectType": "detectionType",
            "r_cfe_timeinstant": "timeinstant",
        }

    # Split rows with and without cfeBlock to process them independently
    df_with_cfe = df[mask_has_cfe].copy()
    df_without_cfe = df[~mask_has_cfe].drop(columns=["cfeBlock"]).copy()
    # Parse timeinstant now so the dtype is consistent when concatenating at the end
    df_without_cfe["timeinstant"] = pd.to_datetime(df_without_cfe["timeinstant"], format="mixed")

    # The CFE block's own timeinstant replaces the parent row's; the parent's is
    # kept only as a fallback for detections that arrive without one
    parent_timeinstant = pd.to_datetime(df_with_cfe.pop("timeinstant"), format="mixed")
    df_with_cfe["_parent_timeinstant"] = parent_timeinstant
    df_with_cfe["cfeBlock"] = df_with_cfe["cfeBlock"].apply(_parse_cfe_block)
    # A single detection arrives as a dict: explode() would split it into its keys
    df_with_cfe["cfeBlock"] = df_with_cfe["cfeBlock"].apply(
        lambda x: [x] if isinstance(x, dict) else x
    )
    # Each element in the cfeBlock array becomes its own row. An empty block
    # explodes to NaN and carries no detection: drop it instead of writing a
    # row with only the entityId
    df_with_cfe = df_with_cfe.explode("cfeBlock")
    df_with_cfe = df_with_cfe[df_with_cfe["cfeBlock"].apply(lambda x: isinstance(x, dict))]
    df_with_cfe = df_with_cfe.reset_index(drop=True)
    df_cfe = pd.json_normalize(df_with_cfe["cfeBlock"].tolist(), max_level=0)
    df_cfe.rename(columns=measures_renames, inplace=True)

    target_columns = list(dict.fromkeys(measures_renames.values()))
    if keep_unmapped_fields:
        unmapped = {
            c: c[len(CFE_BLOCK_PREFIX):]
            for c in df_cfe.columns
            if c.startswith(CFE_BLOCK_PREFIX) and c not in measures_renames
        }
        df_cfe.rename(columns=unmapped, inplace=True)
        for column in unmapped.values():
            df_cfe[column] = df_cfe[column].apply(_to_json_if_nested)
        target_columns += [c for c in unmapped.values() if c not in target_columns]

    if "timeinstant" in df_cfe.columns:
        df_cfe["timeinstant"] = pd.to_datetime(df_cfe["timeinstant"], unit="s")
    else:
        df_cfe["timeinstant"] = pd.NaT
    df_cfe["timeinstant"] = df_cfe["timeinstant"].fillna(df_with_cfe["_parent_timeinstant"])

    # Ensure all target columns exist (even if NA) and are in a fixed order
    df_cfe[list(set(target_columns) - set(df_cfe.columns))] = pd.NA
    df_cfe = df_cfe[[c for c in target_columns if c in df_cfe.columns]]
    # Drop columns from df_with_cfe that are already in df_cfe to avoid duplicates
    cols_to_drop = ["cfeBlock", "_parent_timeinstant"] + [c for c in target_columns if c in df_with_cfe.columns]
    df_with_cfe = pd.concat([df_with_cfe.drop(columns=cols_to_drop, errors="ignore"), df_cfe], axis=1)

    result = pd.concat([df_without_cfe, df_with_cfe], ignore_index=True)
    return result


def coalesce_legacy_crowd_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Folds the lowercase column names of old cache files onto their camelCase
    name. Renaming instead would leave two columns with the same name when a
    file (or a batch of files) has both, and a later dropna() would drop every row.
    """
    for legacy, canonical in CROWD_LEGACY_COLUMN_ALIASES.items():
        if legacy not in df.columns:
            continue
        if canonical in df.columns:
            df[canonical] = df[canonical].combine_first(df[legacy])
            df = df.drop(columns=[legacy])
        else:
            df = df.rename(columns={legacy: canonical})
    return df


def to_crowd_cache_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalises CrowdFlowEvent rows from both firmware versions to the fixed
    data cache layout (CROWD_CACHE_COLUMNS): integer columns as integers,
    timeinstant as naive UTC ISO 8601, and only rows that are a detection.
    """
    df = coalesce_legacy_crowd_columns(df.copy())

    for column in CROWD_CACHE_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    # Rows without visitorId are not detections: another attribute of the
    # same notification (e.g. period) that landed on its own timestamp
    df = df[df["visitorId"].notna() & (df["visitorId"] != "")]

    for column in CROWD_CACHE_INT_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").round().astype("Int64")

    df["timeinstant"] = pd.to_datetime(
        df["timeinstant"], format="mixed", utc=True, errors="coerce"
    ).dt.tz_localize(None)
    df = df.sort_values("timeinstant", kind="stable")
    df["timeinstant"] = df["timeinstant"].dt.strftime(CROWD_CACHE_TIMEINSTANT_FORMAT)
    df["schemaVersion"] = CROWD_CACHE_SCHEMA_VERSION

    return df[CROWD_CACHE_COLUMNS].reset_index(drop=True)

VISITOR_DAY_KEYS = ["visitorid", "date"]


def aggregate_visitor_days(df: pd.DataFrame) -> pd.DataFrame:
    """Reduces detections to one row per visitor/day with first and last detection."""
    if df is None or df.empty:
        return pd.DataFrame(columns=VISITOR_DAY_KEYS + ["first_seen", "last_seen"])

    times = pd.to_datetime(df["timeinstant"], format="mixed")
    detections = pd.DataFrame(
        {
            "visitorid": df["visitorid"].to_numpy(),
            "date": times.dt.date.to_numpy(),
            "timeinstant": times.to_numpy(),
        }
    )

    return detections.groupby(VISITOR_DAY_KEYS, as_index=False).agg(
        first_seen=("timeinstant", "min"), last_seen=("timeinstant", "max")
    )


def merge_visitor_days(visitor_days: list) -> pd.DataFrame:
    """Merges partial per-visitor/day summaries."""
    frames = [frame for frame in visitor_days if frame is not None and not frame.empty]
    if not frames:
        return pd.DataFrame(columns=VISITOR_DAY_KEYS + ["first_seen", "last_seen"])

    return (
        pd.concat(frames, ignore_index=True)
        .groupby(VISITOR_DAY_KEYS, as_index=False)
        .agg(first_seen=("first_seen", "min"), last_seen=("last_seen", "max"))
    )


def classify_visitor_days(
    visitor_days: pd.DataFrame,
    previous_visitor_types: dict = None,
    resident_threshold_days: int = 2,
    tourist_min_hours: int = 3,
) -> pd.DataFrame:
    """Classifies visitors from per-day summaries. Same rules as classify_visitors."""
    if previous_visitor_types is None:
        previous_visitor_types = {}

    if visitor_days is None or visitor_days.empty:
        return pd.DataFrame(columns=["visitorid", "visitortype"])

    hours_per_day = (
        pd.to_datetime(visitor_days["last_seen"]) - pd.to_datetime(visitor_days["first_seen"])
    ).dt.total_seconds() / 3600

    per_visitor = (
        visitor_days.assign(hours=hours_per_day)
        .groupby("visitorid", sort=False)
        .agg(days=("date", "nunique"), hours=("hours", "sum"))
    )

    previous = per_visitor.index.map(lambda vid: previous_visitor_types.get(vid))
    resident = (per_visitor["days"] > resident_threshold_days) | pd.Series(
        previous, index=per_visitor.index
    ).isin(["Resident", "Tourist"])
    tourist = ~resident & (per_visitor["days"] <= 2) & (per_visitor["hours"] > tourist_min_hours)

    visitor_types = pd.Series("ShortTermVisitor", index=per_visitor.index)
    visitor_types[tourist] = "Tourist"
    visitor_types[resident] = "Resident"

    return pd.DataFrame(
        {"visitorid": per_visitor.index.to_numpy(), "visitortype": visitor_types.to_numpy()}
    )


def classify_visitors(df: pd.DataFrame, previous_visitor_types: dict = None, resident_threshold_days: int = 2, tourist_min_hours: int = 3) -> pd.DataFrame:
        """
        Classifies visitors as 'Resident' or 'Tourist' based on their presence over time.

        Criteria:
        - If a visitor appears on more than resident_threshold_days different days, they are classified as 'Resident'.
        - If a visitor was previously classified as 'Resident' or 'Tourist', they remain 'Resident'.
        - If a visitor appears only on 1-2 days but spends more than tourist_min_hours in total, they are classified as 'Tourist'.
        - Otherwise, they are classified as 'ShortTermVisitor'.

        Args:
            df (pd.DataFrame): DataFrame containing visitor records with 'timeinstant' and 'visitorid'.
            previous_visitor_types (dict): Dictionary mapping visitor_id to visitor_type from previous classifications.
            resident_threshold_days (int): Threshold to classify a visitor as resident (default: 2)
            tourist_min_hours (int): Threshold to classify a visitor as tourist (default: 3)

        Returns:
            pd.DataFrame: DataFrame with unique visitors and their 'visitortype' classification.
        """
        if previous_visitor_types is None:
            previous_visitor_types = {}

        # Preprocess to ensure that timeinstant is in datetime format
        df['timeinstant'] = df['timeinstant'].apply(lambda x: dateutil.parser.parse(x) if isinstance(x, str) else x)
        # Convert 'timeinstant' to datetime
        df['timeinstant'] = pd.to_datetime(df['timeinstant'])

        # Extract date from timeinstant
        df['date'] = df['timeinstant'].dt.date

        # Get unique visitors
        unique_visitors = df['visitorid'].unique()

        # Compute unique days visited per visitor
        visitor_days = df.groupby('visitorid')['date'].nunique()

        # Compute time spent per visitor per day
        visitor_time_spent = df.groupby(['visitorid', 'date'])['timeinstant'].agg(['min', 'max'])
        visitor_time_spent['hours_spent'] = (visitor_time_spent['max'] - visitor_time_spent['min']).dt.total_seconds() / 3600

        # Sum the total hours spent by each visitor
        total_hours_spent = visitor_time_spent.groupby('visitorid')['hours_spent'].sum()

        # Classification logic
        def classify_visitor(vid):
            days = visitor_days.get(vid, 0)
            hours = total_hours_spent.get(vid, 0)
            prev_type = previous_visitor_types.get(vid, None)

            if days > resident_threshold_days or prev_type == 'Resident' or prev_type == 'Tourist':
                return 'Resident'
            elif days <= 2 and hours > tourist_min_hours:
                return 'Tourist'
            else:
                return 'ShortTermVisitor'

        # Create result dataframe with unique visitors
        visitors_df = pd.DataFrame({'visitorid': unique_visitors})
        visitors_df['visitortype'] = visitors_df['visitorid'].map(classify_visitor)

        return visitors_df

def crowd_df_columns_rename(df: pd.DataFrame, municipality: bool = True, random: bool = True, period: bool = True, visitor_type: bool = True):
    if municipality:
        df["municipality"] = "NA"
    if period:
        df["period"] = 5
    if random:
        if "random" not in df.columns :
            df["random"] = False
        else:
            df["random"] = df["random"].fillna(False).astype(bool)
    if visitor_type:
        df["visitorType"] = "Resident"
    renames = {
        "entityId": "entityid",
        "random": "israndommac",
        "visitorId": "visitorid",
        "visitorType": "visitortype",
        "detectionType": "detectiontype",
        "timeinstant": "timeinstant",
    }
    return df.rename(columns=renames)