"""Run the validation checks, log the run and notify n8n.

Steps:
    1. Runs sql/06_validation_checks.sql in BigQuery (rebuilds recruiting.audit_checks)
    2. Reads the results and counts failed checks
    3. Appends one row to recruiting.pipeline_runs (the run log)
    4. Sends a summary to an n8n webhook, which alerts when something failed

Usage (from the repo root):
    python monitoring/run_validations.py

Environment variables (.env):
    GCP_PROJECT_ID, BQ_DATASET (default: recruiting), N8N_VALIDATION_WEBHOOK_URL
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET = os.getenv("BQ_DATASET", "recruiting")
WEBHOOK_URL = os.getenv("N8N_VALIDATION_WEBHOOK_URL")
SQL_PATH = Path("sql/06_validation_checks.sql")

RUN_SCHEMA = [
    bigquery.SchemaField("run_id", "STRING"),
    bigquery.SchemaField("run_type", "STRING"),
    bigquery.SchemaField("started_at", "TIMESTAMP"),
    bigquery.SchemaField("finished_at", "TIMESTAMP"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("checks_total", "INTEGER"),
    bigquery.SchemaField("checks_failed", "INTEGER"),
    bigquery.SchemaField("error_message", "STRING"),
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def run_checks(client) -> list:
    """Rebuild the audit table and return its rows."""
    client.query(SQL_PATH.read_text(encoding="utf-8")).result()
    query = (
        "SELECT check_type, check_name, description, expected, actual, status "
        f"FROM `{PROJECT_ID}.{DATASET}.audit_checks` ORDER BY check_type, check_name"
    )
    return [dict(row) for row in client.query(query).result()]


def build_payload(run_id: str, status: str, results: list, error) -> dict:
    failures = [r for r in results if r["status"] != "PASS"]
    if error:
        failures = [
            {"check_type": "error", "check_name": "pipeline_error", "description": error,
             "expected": None, "actual": None, "status": "FAIL"}
        ]
    total = len(results)
    return {
        "source": "validation",
        "project": "sales-vacancies",
        "run_id": run_id,
        "status": status,
        "total": total,
        "failed": len(failures),
        "passed": total - len(failures) if not error else 0,
        "failures": failures,
    }


def log_run(client, record: dict) -> None:
    job = client.load_table_from_json(
        [record],
        f"{PROJECT_ID}.{DATASET}.pipeline_runs",
        job_config=bigquery.LoadJobConfig(schema=RUN_SCHEMA, write_disposition="WRITE_APPEND"),
    )
    job.result()


def send_to_n8n(payload: dict) -> None:
    if not WEBHOOK_URL:
        print("N8N_VALIDATION_WEBHOOK_URL is not set; skipping notification.")
        return
    request = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps(payload, default=str).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(f"Sent summary to n8n (HTTP {response.status}).")
    except urllib.error.URLError as exc:
        print(f"Could not reach n8n at {WEBHOOK_URL}: {exc}")


def main() -> None:
    if not PROJECT_ID:
        raise SystemExit("GCP_PROJECT_ID is not set. Copy .env.example to .env and fill it in.")

    client = bigquery.Client(project=PROJECT_ID)
    run_id = str(uuid.uuid4())
    started = now()

    error = None
    results = []
    try:
        results = run_checks(client)
        failed = [r for r in results if r["status"] != "PASS"]
        status = "failed_checks" if failed else "success"
    except Exception as exc:  # any BigQuery or file error is logged as a failed run
        status, error = "error", str(exc)[:500]

    payload = build_payload(run_id, status, results, error)
    record = {
        "run_id": run_id,
        "run_type": "validation",
        "started_at": started,
        "finished_at": now(),
        "status": status,
        "checks_total": payload["total"],
        "checks_failed": payload["failed"],
        "error_message": error,
    }
    try:
        log_run(client, record)
        print("Run logged in pipeline_runs.")
    except Exception as exc:
        print(f"Could not write to pipeline_runs: {exc}")

    print(f"\nStatus: {status}. {payload['passed']} passed, {payload['failed']} failed of {payload['total']}.")
    for f in payload["failures"]:
        print(f"  FAIL {f['check_name']}: expected {f['expected']}, got {f['actual']}" if not error else f"  ERROR {f['description']}")

    send_to_n8n(payload)
    sys.exit(0 if status == "success" else 1)


if __name__ == "__main__":
    main()
