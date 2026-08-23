"""
Orchestrates the ingestion step of the Retail Sales Intelligence Pipeline.

This is Airflow's entry point for the pipeline — it doesn't contain the actual
ingestion logic (that lives in scripts/ingestion/ingest_orders.py), it just
schedules and monitors that existing script.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from scripts.ingestion.ingest_orders import run_ingestion


def run_ingestion_task(**context):
    """
    Wraps run_ingestion() so Airflow can properly detect failure.

    Why this wrapper exists: run_ingestion() returns True/False rather than
    raising an exception on failure (that was a deliberate Phase 1 choice, so
    the script works cleanly as a CLI tool with an exit code). But Airflow's
    PythonOperator only considers a task failed if the Python callable raises
    an exception — a function that returns False but doesn't raise is
    considered a SUCCESS by Airflow. So we translate "returned False" into
    "raise an exception" here, specifically for Airflow's benefit.
    """
    success = run_ingestion()
    if not success:
        raise RuntimeError("Ingestion run failed — check logs for which file(s) failed validation.")


default_args = {
    "owner": "aryan",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="retail_pipeline_ingestion",
    description="Downloads and validates the Olist dataset into the raw layer",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 8, 1),
    catchup=False,
    tags=["retail-pipeline", "ingestion"],
) as dag:

    ingest_task = PythonOperator(
        task_id="ingest_and_validate_orders",
        python_callable=run_ingestion_task,
    )

    ingest_task