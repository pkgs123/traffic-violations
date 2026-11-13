"""Clean the raw Traffic Violations CSV and save it as a Parquet file."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAW_FILE = Path("data/raw/Traffic_Violations.csv")
CLEAN_FILE = Path("data/clean/traffic_violations_clean.parquet")

DROP_RAW_COLUMNS = ["Geolocation", "Agency"]  # redundant / single value
COLUMN_RENAMES = {
    "seqid": "seq_id",
    "subagency": "sub_agency",
    "vehicletype": "vehicle_type",
    "year": "vehicle_year",
}
YES_NO_COLUMNS = [
    "accident",
    "belts",
    "personal_injury",
    "property_damage",
    "fatal",
    "commercial_license",
    "hazmat",
    "commercial_vehicle",
    "alcohol",
    "work_zone",
    "search_conducted",
    "contributed_to_accident",
]
SEARCH_COLUMNS = [
    "search_disposition",
    "search_outcome",
    "search_reason",
    "search_reason_for_stop",
    "search_type",
    "search_arrest_reason",
]
TEXT_COLUMNS = [
    "sub_agency",
    "description",
    "location",
    "state",
    "vehicle_type",
    "make",
    "model",
    "color",
    "violation_type",
    "charge",
    "article",
    "race",
    "gender",
    "driver_city",
    "driver_state",
    "dl_state",
    "arrest_type",
] + SEARCH_COLUMNS
CATEGORY_COLUMNS = [c for c in TEXT_COLUMNS if c not in ("location", "description")] + [
    "time_of_day",
    "violation_category",
    "severity",
    "stop_weekday",
]

MAKE_FIXES = {
    "TOYT": "TOYOTA",
    "HOND": "HONDA",
    "CHEV": "CHEVROLET",
    "CHEVY": "CHEVROLET",
    "NISS": "NISSAN",
    "MERZ": "MERCEDES-BENZ",
    "MERCEDES": "MERCEDES-BENZ",
    "HYUN": "HYUNDAI",
    "ACUR": "ACURA",
    "DODG": "DODGE",
    "VOLK": "VOLKSWAGEN",
    "VOLKSWAGON": "VOLKSWAGEN",
    "VW": "VOLKSWAGEN",
    "MAZD": "MAZDA",
    "CHRY": "CHRYSLER",
    "MITS": "MITSUBISHI",
    "SUBA": "SUBARU",
    "CADI": "CADILLAC",
    "INFI": "INFINITI",
    "LEXS": "LEXUS",
    "NONE": "UNKNOWN",
}
COLOR_FIXES = {
    "BLUE, DARK": "BLUE",
    "BLUE, LIGHT": "BLUE",
    "GREEN, DK": "GREEN",
    "GREEN, LGT": "GREEN",
}
# (keyword found in description, category label) - first match wins
# VIOLATION_KEYWORDS = [
#     ("SPEED", "SPEEDING"),
#     ("SEAT BELT", "SEAT BELT"),
#     ("LICENSE", "LICENSE"),
#     ("REGISTR", "REGISTRATION"),
#     ("INSURANCE", "INSURANCE"),
#     ("PHONE", "PHONE USE"),
#     ("LIGHT", "LIGHTS / EQUIPMENT"),
# ]
VIOLATION_KEYWORDS = [
    ("ALCOHOL|INFLUENCE|IMPAIRED|\\bDUI\\b", "ALCOHOL / DUI"),
    ("SPEED", "SPEEDING"),
    ("SEAT ?BELT|RESTRAINED", "SEAT BELT"),
    ("LICENSE|\\bLIC\\b|PERMIT", "LICENSE"),
    ("REGIST|\\bREG\\b|PLATE|TAB ON", "REGISTRATION"),
    ("INSUR|SECURITY", "INSURANCE"),
    ("PHONE|HANDHELD|HAND-HELD|TEXT", "PHONE USE"),
    ("TINT|GLASS", "WINDOW TINT"),
    ("RECKLESS|NEGLIGENT|CARELESS", "RECKLESS DRIVING"),
    (
        "STOP SIGN|\\bSIGN\\b|\\bRED\\b|SIGNAL|TRAFFIC CONTROL|YIELD|LANE|RIGHT.OF.WAY|CROSSWALK",
        "TRAFFIC SIGNAL / ROAD RULES",
    ),
    ("LIGHT|LAMP|EQUIP", "LIGHTS / EQUIPMENT"),
    ("PARK", "PARKING"),
]
# Rough bounding box for Maryland
LAT_RANGE = (37.8, 39.8)
LON_RANGE = (-79.6, -75.0)


def load_raw_data(sample_rows=None):
    """Read the raw CSV (optionally only the first N rows for testing)."""
    return pd.read_csv(
        RAW_FILE,
        nrows=sample_rows,
        usecols=lambda column: column not in DROP_RAW_COLUMNS,
        low_memory=False,
    )


def standardize_column_names(df):
    """Make column names lowercase_with_underscores."""
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df.rename(columns=COLUMN_RENAMES)


def standardize_text(df):
    """Strip spaces and convert text columns to uppercase."""
    for column in TEXT_COLUMNS:
        df[column] = df[column].astype("string").str.strip().str.upper()
    return df


def to_boolean(series):
    """Convert Yes/No style values to True/False (blank -> False)."""
    mapping = {
        "YES": True,
        "Y": True,
        "TRUE": True,
        "NO": False,
        "N": False,
        "FALSE": False,
    }
    return series.astype(str).str.strip().str.upper().map(mapping).fillna(False)


def clean_dates_and_times(df):
    """Parse dates, fix time separators, drop invalid or future dates."""
    df["date_of_stop"] = pd.to_datetime(
        df["date_of_stop"], format="%m/%d/%Y", errors="coerce"
    )
    time_text = df["time_of_stop"].astype(str).str.replace(".", ":", regex=False)
    df["stop_hour"] = pd.to_datetime(
        time_text, format="%H:%M:%S", errors="coerce"
    ).dt.hour
    valid = df["date_of_stop"].notna() & (df["date_of_stop"] <= pd.Timestamp.now())
    return df[valid].drop(columns=["time_of_stop"])


def clean_coordinates(df):
    """Replace zero or out-of-range coordinates with NaN."""
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    bad = ~df["latitude"].between(*LAT_RANGE) | ~df["longitude"].between(*LON_RANGE)
    df.loc[bad, ["latitude", "longitude"]] = np.nan
    return df


def clean_vehicle_columns(df):
    """Fix vehicle year, make and color."""
    df["vehicle_year"] = pd.to_numeric(df["vehicle_year"], errors="coerce")
    max_year = pd.Timestamp.now().year + 1
    df.loc[~df["vehicle_year"].between(1960, max_year), "vehicle_year"] = np.nan
    df["make"] = df["make"].replace(MAKE_FIXES).fillna("UNKNOWN")
    df["color"] = df["color"].replace(COLOR_FIXES).fillna("UNKNOWN")
    df["model"] = df["model"].fillna("UNKNOWN")
    return df


def clean_driver_columns(df):
    """Standardize gender and fill blanks in other driver/search columns."""
    df["gender"] = df["gender"].where(df["gender"].isin(["M", "F"]), "UNKNOWN")
    for column in SEARCH_COLUMNS:
        df[column] = df[column].fillna("NOT APPLICABLE")
    for column in ["race", "driver_city", "driver_state", "dl_state", "state"]:
        df[column] = df[column].fillna("UNKNOWN")
    return df


def add_features(df):
    """Create new columns that make analysis easier."""
    df["stop_year"] = df["date_of_stop"].dt.year
    df["stop_month"] = df["date_of_stop"].dt.month
    df["stop_weekday"] = df["date_of_stop"].dt.day_name()

    hour = df["stop_hour"]
    df["time_of_day"] = np.select(
        [hour.isna(), hour.between(5, 11), hour.between(12, 16), hour.between(17, 20)],
        ["UNKNOWN", "MORNING", "AFTERNOON", "EVENING"],
        default="NIGHT",
    )

    conditions = [
        df["description"].str.contains(k, na=False) for k, _ in VIOLATION_KEYWORDS
    ]
    labels = [label for _, label in VIOLATION_KEYWORDS]
    df["violation_category"] = np.select(conditions, labels, default="OTHER")

    df["severity"] = np.select(
        [df["fatal"], df["personal_injury"], df["property_damage"]],
        ["FATAL", "INJURY", "PROPERTY DAMAGE"],
        default="NONE",
    )
    df["charges_per_stop"] = (
        df.groupby("seq_id", sort=False)["seq_id"].transform("size").astype("int16")
    )
    return df


def optimize_dtypes(df):
    """Shrink memory use with category and smaller numeric types."""
    for column in CATEGORY_COLUMNS:
        df[column] = df[column].astype("category")
    df["latitude"] = df["latitude"].astype("float32")
    df["longitude"] = df["longitude"].astype("float32")
    df["vehicle_year"] = df["vehicle_year"].astype("Int16")
    df["stop_year"] = df["stop_year"].astype("int16")
    df["stop_month"] = df["stop_month"].astype("int8")
    df["stop_hour"] = df["stop_hour"].astype("Int8")
    return df


def clean(df):
    """Run every cleaning step in order."""
    df = standardize_column_names(df)
    rows_before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    print(f"Removed {rows_before - len(df):,} fully duplicate rows")

    df["seq_id"] = df["seq_id"].astype("string")
    df = standardize_text(df)
    for column in YES_NO_COLUMNS:
        df[column] = to_boolean(df[column])
    df = clean_dates_and_times(df)
    df = clean_coordinates(df)
    df = clean_vehicle_columns(df)
    df = clean_driver_columns(df)
    df = add_features(df)
    return optimize_dtypes(df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="only process the first N rows (for testing)",
    )
    args = parser.parse_args()

    try:
        raw_df = load_raw_data(args.sample)
    except FileNotFoundError:
        print(f"Cannot find {RAW_FILE}. Put Traffic_Violations.csv in data/raw/ first.")
        return
    print(f"Loaded {len(raw_df):,} rows")

    clean_df = clean(raw_df)
    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_parquet(CLEAN_FILE, index=False)
    print(f"Saved {len(clean_df):,} rows to {CLEAN_FILE}")


if __name__ == "__main__":
    main()
