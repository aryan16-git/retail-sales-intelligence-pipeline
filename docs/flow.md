# Execution Flow — Retail Sales Intelligence Pipeline

This document tracks how execution actually moves through the codebase: entry points,
call order, and what changed each phase. Updated every phase as real code lands.

## Status: Phase 0 complete — no runtime code yet

No entry point exists yet. This is scaffolding only:
conda env, folder structure, git repo, decision log.

## Planned entry points (filled in as built)

- Phase 1: `scripts/ingestion/ingest_orders.py` — manual/CLI entry point for raw ingestion
- Phase 2: `dags/retail_pipeline_dag.py` — Airflow entry point, calls Phase 1's ingestion script as a task
- Phase 4: `dbt_project/` — `dbt run` / `dbt test` as the transformation entry point, triggered as an Airflow task in the same DAG

## Change log (chronological, cross-referenced to docs/decision.md IDs)

- 2026-08-12 — Phase 0: created project scaffolding (folders, environment.yml, git repo, .gitignore). See D001–D005 in decision.md. No functions/modules exist yet.

## Status: Phase 1 in complete — ingestion entry point live

## Entry points

- `python -m scripts.ingestion.ingest_orders` — CLI entry point for manual runs
- Internally calls `run_ingestion()`, which is the function Airflow will call directly in Phase 2 (see D008)

## Call chain: scripts/ingestion/ingest_orders.py

1. `__main__` calls `run_ingestion()`
2. `run_ingestion()` calls `download_dataset()`
   - authenticates with Kaggle API (reads ~/.kaggle/kaggle.json)
   - downloads dataset zip to data/raw/olist/
   - extracts zip contents, deletes the zip
3. `run_ingestion()` then calls `validate_file()` once per file in `EXPECTED_SCHEMA`
   - each call: checks file exists -> checks row count -> checks expected columns -> logs null audit
4. `run_ingestion()` aggregates pass/fail across all files, logs summary, returns True/False
5. `__main__` converts that to a process exit code (0 = success, 1 = failure) — this is what Airflow will read in Phase 2

## Change log

- 2026-08-23 — Phase 1: added scripts/utils/logging_config.py (shared logger) and scripts/ingestion/ingest_orders.py (download + validate). See D008, D009 in decision.md.

- 2026-08-23 — Phase 1 complete: verified full ingestion run (9/9 files, 99,441 orders etc.), added idempotency check (raw_files_already_valid), added tests/test_ingestion.py (4 tests, all passing), added pytest.ini for import resolution. See D010, D011 in decision.md.