"""
Tests for the ingestion validation logic.
Note: these test validate_file() against small in-memory/temp CSVs, not the real
42MB dataset — fast, deterministic, and don't require network access to run.
"""

import pandas as pd
import pytest

from scripts.ingestion.ingest_orders import validate_file, RAW_DIR


@pytest.fixture
def temp_raw_file(tmp_path, monkeypatch):
    """Points RAW_DIR at a temp directory for the duration of each test,
    so tests never touch your real data/raw/olist/ files."""
    monkeypatch.setattr("scripts.ingestion.ingest_orders.RAW_DIR", tmp_path)
    return tmp_path


def test_validate_file_passes_with_correct_schema(temp_raw_file):
    df = pd.DataFrame({
        "order_id": [f"o{i}" for i in range(100)],
        "customer_id": [f"c{i}" for i in range(100)],
        "order_status": ["delivered"] * 100,
        "order_purchase_timestamp": ["2024-01-01"] * 100,
        "order_delivered_customer_date": ["2024-01-05"] * 100,
    })
    df.to_csv(temp_raw_file / "olist_orders_dataset.csv", index=False)

    result = validate_file(
        "olist_orders_dataset.csv",
        ["order_id", "customer_id", "order_status",
         "order_purchase_timestamp", "order_delivered_customer_date"],
    )
    assert result is True


def test_validate_file_fails_on_missing_column(temp_raw_file):
    df = pd.DataFrame({"order_id": [f"o{i}" for i in range(100)]})
    df.to_csv(temp_raw_file / "olist_orders_dataset.csv", index=False)

    result = validate_file("olist_orders_dataset.csv", ["order_id", "customer_id"])
    assert result is False


def test_validate_file_fails_on_too_few_rows(temp_raw_file):
    df = pd.DataFrame({"order_id": ["o1", "o2"]})  # only 2 rows, below MIN_ROW_COUNT
    df.to_csv(temp_raw_file / "olist_orders_dataset.csv", index=False)

    result = validate_file("olist_orders_dataset.csv", ["order_id"])
    assert result is False


def test_validate_file_fails_when_file_missing(temp_raw_file):
    result = validate_file("does_not_exist.csv", ["order_id"])
    assert result is False