import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "environmental_data_multisite_7days.csv"

CLEAN_FILE = "ml_dataset_clean.csv"
REPORT_FILE = "data_quality_report.txt"


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("HEAT RISK ML DATA PREPARATION")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Original shape: {df.shape}")


# ============================================================
# BASIC INFORMATION
# ============================================================

print("\n" + "=" * 70)
print("1. BASIC INFORMATION")
print("=" * 70)

print("\nColumns:")
for i, column in enumerate(df.columns, 1):
    print(f"{i:02d}. {column}")


# ============================================================
# TIMESTAMP
# ============================================================

print("\n" + "=" * 70)
print("2. TIMESTAMP CHECK")
print("=" * 70)

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

invalid_timestamps = df["timestamp"].isna().sum()

print(f"Invalid timestamps: {invalid_timestamps}")

print(
    f"Date range: "
    f"{df['timestamp'].min()} → {df['timestamp'].max()}"
)


# ============================================================
# DUPLICATES
# ============================================================

print("\n" + "=" * 70)
print("3. DUPLICATE CHECK")
print("=" * 70)

duplicates = df.duplicated(
    subset=["site_id", "timestamp"]
).sum()

print(f"Duplicate rows: {duplicates}")

if duplicates > 0:
    df = df.drop_duplicates(
        subset=["site_id", "timestamp"]
    )

    print(
        f"Shape after duplicate removal: {df.shape}"
    )


# ============================================================
# MISSING VALUES
# ============================================================

print("\n" + "=" * 70)
print("4. MISSING VALUES")
print("=" * 70)

missing = df.isnull().sum()

missing = missing[missing > 0]

if len(missing) == 0:

    print("No missing values found.")

else:

    print(missing)


# ============================================================
# SITES
# ============================================================

print("\n" + "=" * 70)
print("5. SITE ANALYSIS")
print("=" * 70)

site_counts = (
    df.groupby("site_id")
      .size()
      .sort_index()
)

print("\nRows per site:")

print(site_counts)


# ============================================================
# EXPECTED HOURLY DATA
# ============================================================

print("\n" + "=" * 70)
print("6. HOURLY COVERAGE")
print("=" * 70)

expected_hours_per_site = 7 * 24

print(
    f"Expected hours/site: "
    f"{expected_hours_per_site}"
)

for site_id in sorted(df["site_id"].unique()):

    site_df = df[
        df["site_id"] == site_id
    ].copy()

    site_df = site_df.sort_values(
        "timestamp"
    )

    actual = len(site_df)

    missing_hours = (
        expected_hours_per_site - actual
    )

    print(
        f"{site_id}: "
        f"{actual} rows | "
        f"{missing_hours} missing"
    )


# ============================================================
# HOURLY GAPS
# ============================================================

print("\n" + "=" * 70)
print("7. TIMESTAMP GAPS")
print("=" * 70)

for site_id in sorted(df["site_id"].unique()):

    site_df = df[
        df["site_id"] == site_id
    ].copy()

    site_df = site_df.sort_values(
        "timestamp"
    )

    time_diff = (
        site_df["timestamp"]
        .diff()
        .dropna()
    )

    gaps = time_diff[
        time_diff > pd.Timedelta(hours=1)
    ]

    if len(gaps) == 0:

        print(
            f"{site_id}: No hourly gaps"
        )

    else:

        print(
            f"{site_id}: "
            f"{len(gaps)} gap(s)"
        )

        for index in gaps.index:

            previous_time = site_df.loc[
                index - 1,
                "timestamp"
            ]

            current_time = site_df.loc[
                index,
                "timestamp"
            ]

            print(
                f"   {previous_time} "
                f"→ {current_time}"
            )


# ============================================================
# NUMERIC SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("8. HEAT VARIABLES")
print("=" * 70)

heat_columns = [
    "heat_index_celsius",
    "apparent_temperature_celsius",
    "relative_humidity_percent",
    "wet_bulb_temperature_celsius",
]


available_heat_columns = [
    col
    for col in heat_columns
    if col in df.columns
]


print(
    df[available_heat_columns].describe()
)


# ============================================================
# HEAT INDEX DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("9. HEAT INDEX DISTRIBUTION")
print("=" * 70)

heat = df["heat_index_celsius"]

print(
    f"Minimum : {heat.min():.2f}"
)

print(
    f"Mean    : {heat.mean():.2f}"
)

print(
    f"Median  : {heat.median():.2f}"
)

print(
    f"Maximum : {heat.max():.2f}"
)


# ============================================================
# POTENTIAL RISK DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("10. HEAT LEVEL COUNTS")
print("=" * 70)

low = (heat < 35).sum()

medium = (
    (heat >= 35) &
    (heat < 40)
).sum()

high = (heat >= 40).sum()

print(
    f"Below 35°C : {low}"
)

print(
    f"35–39.9°C  : {medium}"
)

print(
    f"40°C+      : {high}"
)

print(
    f"Total      : {len(df)}"
)


# ============================================================
# ADD TIME FEATURES
# ============================================================

print("\n" + "=" * 70)
print("11. FEATURE ENGINEERING")
print("=" * 70)

df["hour"] = df["timestamp"].dt.hour

df["day_of_week"] = (
    df["timestamp"].dt.dayofweek
)

df["day"] = (
    df["timestamp"].dt.day
)

df["month"] = (
    df["timestamp"].dt.month
)


print(
    "Added:"
)

print(
    "hour, day_of_week, day, month"
)


# ============================================================
# ADD SIMPLE HEAT CATEGORIES
# ============================================================

def classify_heat_index(value):

    if value < 35:
        return "LOW"

    elif value < 40:
        return "MEDIUM"

    else:
        return "HIGH"


df["heat_level"] = (
    df["heat_index_celsius"]
    .apply(classify_heat_index)
)


print("\nHeat level distribution:")

print(
    df["heat_level"]
    .value_counts()
    .sort_index()
)


# ============================================================
# CHECK CLASS BALANCE
# ============================================================

print("\n" + "=" * 70)
print("12. CLASS BALANCE")
print("=" * 70)

class_counts = (
    df["heat_level"]
    .value_counts()
)

class_percentages = (
    df["heat_level"]
    .value_counts(
        normalize=True
    ) * 100
)

for class_name in [
    "LOW",
    "MEDIUM",
    "HIGH"
]:

    count = class_counts.get(
        class_name,
        0
    )

    percentage = class_percentages.get(
        class_name,
        0
    )

    print(
        f"{class_name:7s}: "
        f"{count:4d} "
        f"({percentage:.2f}%)"
    )


# ============================================================
# SAVE CLEAN DATASET
# ============================================================

print("\n" + "=" * 70)
print("13. SAVE DATASET")
print("=" * 70)

df.to_csv(
    CLEAN_FILE,
    index=False
)

print(
    f"Saved clean dataset to: "
    f"{CLEAN_FILE}"
)


# ============================================================
# GENERATE REPORT
# ============================================================

with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "HEAT RISK DATA QUALITY REPORT\n"
    )

    f.write(
        "=" * 50 + "\n\n"
    )

    f.write(
        f"Original shape: {df.shape}\n"
    )

    f.write(
        f"Date range: "
        f"{df['timestamp'].min()} "
        f"-> "
        f"{df['timestamp'].max()}\n\n"
    )

    f.write(
        "Rows per site:\n"
    )

    f.write(
        site_counts.to_string()
    )

    f.write(
        "\n\nMissing values:\n"
    )

    f.write(
        df.isnull()
          .sum()
          .to_string()
    )

    f.write(
        "\n\nHeat level distribution:\n"
    )

    f.write(
        df["heat_level"]
          .value_counts()
          .to_string()
    )


print(
    f"Saved report to: "
    f"{REPORT_FILE}"
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("PREPARATION COMPLETED")
print("=" * 70)

print(
    f"Final shape: {df.shape}"
)

print(
    "\nNext step:"
)

print(
    "Review the output before training the ML model."
)