"""
Product Analytics ETL — daily orchestration.

Flow:
    ingest_csv  ->  dbt_run  ->  dbt_test
    (export_to_bigquery is disabled until GCP credentials are configured)
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

PROJECT_ROOT = Path("/opt/airflow/project")  # mounted in docker-compose
DBT_DIR      = PROJECT_ROOT / "dbt"
INGEST_FILE  = PROJECT_ROOT / "ingestion" / "load_csv_to_postgres.py"

default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def run_ingestion() -> None:
    """Invoke the ingestion script inside Airflow's Python process."""
    # Add ingestion/ to sys.path so `from config import ...` resolves.
    ingestion_dir = str(INGEST_FILE.parent)
    if ingestion_dir not in sys.path:
        sys.path.insert(0, ingestion_dir)
    import runpy
    runpy.run_path(str(INGEST_FILE), run_name="__main__")


with DAG(
    dag_id="product_analytics_etl",
    description="CSV → Postgres → dbt",
    default_args=default_args,
    start_date=datetime(2026, 5, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["analytics", "dbt", "etl"],
) as dag:

    ingest_csv = PythonOperator(
        task_id="ingest_csv_to_postgres",
        python_callable=run_ingestion,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt deps --quiet && dbt run --target dev",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --target dev",
    )

    # export_to_bq is disabled — enable once GCP credentials are mounted.
    # export_to_bq = BashOperator(
    #     task_id="export_to_bigquery",
    #     bash_command=f"cd {DBT_DIR} && dbt run --target prod --select marts",
    # )

    ingest_csv >> dbt_run >> dbt_test
