"""Load the synthetic recruiting tables into BigQuery (dataset: recruiting).

Dates are loaded as DATE columns so they can be queried directly in SQL.
Each run replaces the tables (WRITE_TRUNCATE), so it is safe to re-run.

Usage:
    python ingestion/load_to_bigquery.py
"""
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET = os.getenv("BQ_DATASET", "recruiting")
LOCATION = os.getenv("BQ_LOCATION", "US")
DATA_DIR = Path("data/generated")

DATE_COLUMNS = {
    "clients": ["signed_at"],
    "vacancies": ["opened_at", "closed_at"],
    "candidates": ["created_at"],
    "applications": ["applied_at"],
    "placements": ["placed_at"],
    "marketing_daily": ["date"],
    "sales_deals": ["created_at", "closed_at"],
}


def prepare(table: str, df: pd.DataFrame) -> pd.DataFrame:
    """Convert date columns to real dates (empty values become NULL)."""
    df = df.copy()
    for col in DATE_COLUMNS.get(table, []):
        parsed = pd.to_datetime(df[col])
        df[col] = parsed.dt.date.where(parsed.notna(), None)
    df["_loaded_at"] = datetime.now(timezone.utc)
    return df


def main() -> None:
    if not PROJECT_ID:
        raise SystemExit("GCP_PROJECT_ID is not set. Copy .env.example to .env and fill it in.")

    client = bigquery.Client(project=PROJECT_ID)
    dataset = bigquery.Dataset(f"{PROJECT_ID}.{DATASET}")
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)

    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV files in {DATA_DIR}. Run data_generation/generate_recruiting_data.py first.")

    for path in files:
        table = path.stem
        df = prepare(table, pd.read_csv(path))
        table_id = f"{PROJECT_ID}.{DATASET}.{table}"
        job = client.load_table_from_dataframe(
            df, table_id, job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        )
        job.result()
        print(f"  OK  {table_id}: {len(df):,} rows")
    print("Done.")


if __name__ == "__main__":
    main()
