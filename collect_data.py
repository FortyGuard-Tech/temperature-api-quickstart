import os
import time
import pandas as pd

from dotenv import load_dotenv
from fortyguard import FortyGuardClient


# ============================================================
# CONFIGURATION
# ============================================================

START_DATE = "2026-07-20"
END_DATE = "2026-07-26"

# Approximate temperature used by the environmental endpoint.
# We will NOT use this as the ML target.
TEMPERATURE = 32.25

OUTPUT_FILE = "environmental_data_multisite_7days.csv"


# ============================================================
# LOCATIONS
# ============================================================

LOCATIONS = [
    {
        "site_id": "site_1",
        "latitude": 40.716452,
        "longitude": -73.987041,
    },
    {
        "site_id": "site_2",
        "latitude": 40.730610,
        "longitude": -73.935242,
    },
    {
        "site_id": "site_3",
        "latitude": 40.748817,
        "longitude": -73.985428,
    },
    {
        "site_id": "site_4",
        "latitude": 40.758896,
        "longitude": -73.985130,
    },
    {
        "site_id": "site_5",
        "latitude": 40.783060,
        "longitude": -73.971250,
    },
]


# ============================================================
# LOAD API KEY
# ============================================================

load_dotenv()

api_key = os.getenv("FORTYGUARD_API_KEY")

if not api_key:
    raise ValueError(
        "FORTYGUARD_API_KEY is missing from .env"
    )

client = FortyGuardClient(api_key=api_key)


# ============================================================
# COLLECT ONE DAY FOR ONE LOCATION
# ============================================================

def collect_one_day(site, date):

    print(
        f"Collecting | "
        f"{site['site_id']} | "
        f"{date}"
    )

    response = client.environmental_parameters(
        latitude=site["latitude"],
        longitude=site["longitude"],
        temperature=TEMPERATURE,

        start_date=date,
        start_time="00:00",

        end_date=date,
        end_time="23:00",

        filter_type=2,
    )

    result = response["result"]

    metadata = result["metadata"]
    location = result["locations"][0]

    timestamps = metadata["timestamps"]
    parameters = location["parameters"]

    data = {
        "site_id": site["site_id"],
        "timestamp": timestamps,

        "latitude": location["lat"],
        "longitude": location["lon"],
        "elevation": location["elevation"],
    }

    for name, values in parameters.items():
        data[name] = values

    df = pd.DataFrame(data)

    print(f"    Rows: {len(df)}")

    return df


# ============================================================
# MAIN COLLECTION
# ============================================================

all_data = []

dates = pd.date_range(
    START_DATE,
    END_DATE,
    freq="D"
)

total_requests = len(LOCATIONS) * len(dates)

print("=" * 60)
print("FORTYGUARD MULTI-SITE DATA COLLECTION")
print("=" * 60)
print(f"Locations : {len(LOCATIONS)}")
print(f"Days      : {len(dates)}")
print(f"Requests  : {total_requests}")
print("=" * 60)


request_number = 0


for site in LOCATIONS:

    for date in dates:

        request_number += 1

        date_str = date.strftime("%Y-%m-%d")

        print(
            f"\n[{request_number}/{total_requests}]"
        )

        try:

            day_df = collect_one_day(
                site,
                date_str
            )

            all_data.append(day_df)

        except Exception as e:

            print(
                f"ERROR | "
                f"{site['site_id']} | "
                f"{date_str}"
            )

            print(e)

            # Continue with the next request
            continue


# ============================================================
# CHECK RESULT
# ============================================================

if not all_data:

    raise RuntimeError(
        "No data was collected."
    )


# ============================================================
# COMBINE DATA
# ============================================================

df = pd.concat(
    all_data,
    ignore_index=True
)


# ============================================================
# CLEAN TIMESTAMP
# ============================================================

df["timestamp"] = pd.to_datetime(
    df["timestamp"]
)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

df = df.drop_duplicates(
    subset=[
        "site_id",
        "timestamp"
    ]
)


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    [
        "site_id",
        "timestamp"
    ]
).reset_index(drop=True)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 60)
print("COLLECTION COMPLETED")
print("=" * 60)

print(f"Shape: {df.shape}")

print("\nRows per site:")
print(
    df.groupby("site_id").size()
)

print("\nDate range:")
print(df["timestamp"].min())
print(df["timestamp"].max())

print("\nMissing values:")
print(
    df.isnull().sum()
)

print("\nSaved to:")
print(OUTPUT_FILE)

print("=" * 60)