import ast
import pandas as pd
import dateutil.parser
from config.logging import appLogging as logging

def crowd_row_processing_lambda(df, measures_renames = None):
    """
    Custom row processing function to handle specific transformations.
    This can be modified as needed for different ETL processes.
    """

    # Nothing to process
    if df.empty:
        return df

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

    # The CFE block's own timeinstant replaces the parent row's
    df_with_cfe.drop(columns=["timeinstant"], inplace=True)
    df_with_cfe["cfeBlock"] = df_with_cfe["cfeBlock"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    # Each element in the cfeBlock array becomes its own row
    df_with_cfe = df_with_cfe.explode("cfeBlock").reset_index(drop=True)
    df_cfe = pd.json_normalize(df_with_cfe["cfeBlock"])
    df_cfe.rename(columns=measures_renames, inplace=True)
    if "timeinstant" in df_cfe.columns:
        df_cfe["timeinstant"] = pd.to_datetime(df_cfe["timeinstant"], unit="s")

    # Ensure all target columns exist (even if NA) and are in a fixed order
    target_columns = list(dict.fromkeys(measures_renames.values()))
    df_cfe[list(set(target_columns) - set(df_cfe.columns))] = pd.NA
    df_cfe = df_cfe[[c for c in target_columns if c in df_cfe.columns]]
    # Drop columns from df_with_cfe that are already in df_cfe to avoid duplicates
    cols_to_drop = ["cfeBlock"] + [c for c in target_columns if c in df_with_cfe.columns]
    df_with_cfe = pd.concat([df_with_cfe.drop(columns=cols_to_drop, errors="ignore"), df_cfe], axis=1)

    result = pd.concat([df_without_cfe, df_with_cfe], ignore_index=True)
    return result

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