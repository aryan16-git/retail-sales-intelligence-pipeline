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