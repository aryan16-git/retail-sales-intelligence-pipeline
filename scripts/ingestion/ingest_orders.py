"""
Ingestion entry point: downloads the Olist dataset via the Kaggle API,
lands it in data/raw/, and validates what was downloaded before declaring success.

Run manually with:
    python -m scripts.ingestion.ingest_orders

This will also become the function Airflow's PythonOperator calls directly in Phase 2 —
written as functions (not top-level script logic) specifically so Airflow can import
and call `run_ingestion()` without needing to shell out to a subprocess.
"""

import sys
import zipfile
from pathlib import Path

import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi

from scripts.utils.logging_config import get_logger

logger = get_logger(__name__)

KAGGLE_DATASET = "olistbr/brazilian-ecommerce"
RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "olist"

# Minimum expected schema for the tables our downstream models actually depend on.
# Not every column in the source is listed here — only the ones our pipeline can't
# function without. A missing optional column should warn, not crash the pipeline;
# a missing critical column should stop it before bad data reaches the warehouse.
EXPECTED_SCHEMA = {
    "olist_orders_dataset.csv": [
        "order_id", "customer_id", "order_status",
        "order_purchase_timestamp", "order_delivered_customer_date",
    ],
    "olist_order_items_dataset.csv": [
        "order_id", "order_item_id", "product_id", "seller_id", "price",
    ],
    "olist_order_payments_dataset.csv": [
        "order_id", "payment_type", "payment_value",
    ],
    "olist_customers_dataset.csv": [
        "customer_id", "customer_unique_id", "customer_city", "customer_state",
    ],
    "olist_products_dataset.csv": [
        "product_id", "product_category_name",
    ],
    "olist_sellers_dataset.csv": [
        "seller_id", "seller_city", "seller_state",
    ],
    "olist_order_reviews_dataset.csv": [
        "review_id", "order_id", "review_score",
    ],
    "olist_geolocation_dataset.csv": [
        "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
    ],
    "product_category_name_translation.csv": [
        "product_category_name", "product_category_name_english",
    ],
}

# A file with fewer rows than this is almost certainly a partial/corrupt download,
# not a legitimately small dataset — Olist's real files range from hundreds to
# ~100k+ rows. This is a coarse sanity check, not a precise expectation.
MIN_ROW_COUNT = 50


def download_dataset() -> None:
    """Authenticates with Kaggle and downloads+unzips the dataset into data/raw/olist/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting download of Kaggle dataset: {KAGGLE_DATASET}")

    api = KaggleApi()
    api.authenticate()

    zip_path = RAW_DIR / "olist-dataset.zip"
    api.dataset_download_files(KAGGLE_DATASET, path=str(RAW_DIR), quiet=False)

    # The Kaggle client names the zip after the dataset slug, not a fixed name —
    # find whatever .zip landed in RAW_DIR rather than hardcoding its filename.
    downloaded_zips = list(RAW_DIR.glob("*.zip"))
    if not downloaded_zips:
        logger.error("Download appeared to succeed but no .zip file was found in raw dir.")
        raise FileNotFoundError(f"No zip file found in {RAW_DIR} after download.")

    zip_path = downloaded_zips[0]
    logger.info(f"Downloaded: {zip_path.name} ({zip_path.stat().st_size / 1_048_576:.1f} MB)")

    logger.info("Extracting zip contents...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(RAW_DIR)

    zip_path.unlink()  # remove the zip after extraction — no need to keep it around
    logger.info("Extraction complete, zip file removed.")


def validate_file(filename: str, expected_columns: list[str]) -> bool:
    """
    Validates a single raw CSV: exists, has expected columns, has a sane row count,
    and reports null percentages per column. Returns True if validation passed.
    """
    file_path = RAW_DIR / filename

    if not file_path.exists():
        logger.error(f"VALIDATION FAILED: {filename} not found at {file_path}")
        return False

    df = pd.read_csv(file_path)

    row_count = len(df)
    if row_count < MIN_ROW_COUNT:
        logger.error(f"VALIDATION FAILED: {filename} has only {row_count} rows (expected >= {MIN_ROW_COUNT})")
        return False
    logger.info(f"{filename}: {row_count:,} rows")

    missing_columns = [c for c in expected_columns if c not in df.columns]
    if missing_columns:
        logger.error(f"VALIDATION FAILED: {filename} is missing expected columns: {missing_columns}")
        return False

    # Null audit — logged as info, not a failure. A column being 100% null usually
    # signals a real problem (e.g. delivery date nulls for undelivered orders are
    # expected; a *primary key* column being null would not be), so we report
    # percentages and let a human judge severity rather than hardcoding pass/fail
    # thresholds we can't fully justify yet at this stage.
    null_pct = (df.isnull().sum() / len(df) * 100).round(1)
    notable_nulls = null_pct[null_pct > 0].sort_values(ascending=False)
    if not notable_nulls.empty:
        logger.info(f"{filename}: null % by column -> {notable_nulls.to_dict()}")

    logger.info(f"{filename}: validation passed")
    return True

def raw_files_already_valid() -> bool:
    """Checks if a previous successful ingestion already left valid files in place,
    so we can skip re-downloading unchanged data on repeat runs."""
    if not RAW_DIR.exists():
        return False
    return all(
        validate_file(filename, columns)
        for filename, columns in EXPECTED_SCHEMA.items()
    )

def run_ingestion() -> bool:
    """Full ingestion pipeline: download, then validate every expected file. Returns overall success."""
    logger.info("=" * 60)
    logger.info("Starting ingestion run")

    if raw_files_already_valid():
        logger.info("Valid raw files already present — skipping download.")
    else:
        try:
            download_dataset()
        except Exception:
            logger.exception("Download step failed with an unhandled exception")
            return False

    logger.info("Starting validation of downloaded files")
    results = {
        filename: validate_file(filename, columns)
        for filename, columns in EXPECTED_SCHEMA.items()
    }

    passed = sum(results.values())
    total = len(results)
    logger.info(f"Validation summary: {passed}/{total} files passed")

    if passed < total:
        failed_files = [f for f, ok in results.items() if not ok]
        logger.error(f"Ingestion run FAILED. Failed files: {failed_files}")
        return False

    logger.info("Ingestion run completed successfully.")
    return True


if __name__ == "__main__":
    success = run_ingestion()
    sys.exit(0 if success else 1)