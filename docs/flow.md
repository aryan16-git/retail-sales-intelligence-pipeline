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

## Status: Phase 2 complete — orchestration live

## Entry points (updated)

- `dags/retail_pipeline_dag.py` — Airflow's entry point; DAG `retail_pipeline_ingestion`
- DAG's `ingest_and_validate_orders` task (PythonOperator) calls `run_ingestion_task()`, which wraps and calls `run_ingestion()` from Phase 1's `scripts/ingestion/ingest_orders.py`
- Manual CLI entry point (`python -m scripts.ingestion.ingest_orders`) still works independently — same underlying function, two ways to invoke it

## Call chain: dags/retail_pipeline_dag.py

1. Airflow scheduler/dag-processor parses this file, registers DAG `retail_pipeline_ingestion` (schedule: @daily, retries: 2, retry_delay: 5min)
2. On trigger (manual or scheduled): PythonOperator runs `run_ingestion_task()`
3. `run_ingestion_task()` calls `run_ingestion()` (same function from Phase 1 — no duplicated logic)
4. If `run_ingestion()` returns False, `run_ingestion_task()` raises RuntimeError so Airflow correctly marks the task failed (see D014)
5. Verified 2026-08-24: task ran successfully via idempotency skip-path (9/9 files re-validated, no re-download) in ~9 seconds

## Change log

- 2026-08-24 — Phase 2: Astro CLI installed, project initialized, pandas/kaggle added to Airflow's requirements.txt, kaggle.json mounted read-only into scheduler/api-server/dag-processor containers. Built dags/retail_pipeline_dag.py wrapping Phase 1's ingestion script. Verified working end-to-end via Airflow UI. See D012-D015 in decision.md.

## Status: Phase 3 complete — raw layer populated in warehouse via Airflow

## Call chain: dags/retail_pipeline_dag.py (updated)

1. Scheduler/dag-processor parses DAG, registers `retail_pipeline_ingestion`
2. `ingest_and_validate_orders` runs first (Phase 1/2 logic, unchanged)
3. On success, `load_raw_to_warehouse` runs — calls `run_load_task()` -> `run_load()` in scripts/loading/load_to_warehouse.py
4. `run_load()` calls `get_engine()` (resolves AIRFLOW_WAREHOUSE_DB_HOST/PORT when inside a container, WAREHOUSE_DB_HOST/PORT for local runs) then `load_table()` once per file in EXPECTED_SCHEMA, loading each into raw.<table_name> via pandas .to_sql() with if_exists="replace"
5. Verified 2026-08-25: full pipeline run via Airflow UI trigger — both tasks succeeded, 9/9 tables loaded into raw schema with row counts matching source validation exactly

## Change log

- 2026-08-25 — Phase 3: created warehouse-postgres container (raw/staging/marts schemas), built scripts/loading/load_to_warehouse.py, added load_raw_to_warehouse as second DAG task chained after ingestion. Resolved container networking issues (Airflow 3 service names, host-vs-container port mapping, build-time vs live-mounted scripts). See D016-D018 in decision.md.

- 2026-08-25 — Phase 3 verified clean after resolving a transient row-count mismatch caused by overlapping runs during debugging (see D019). Final verification: all 9 raw tables match source row counts exactly.