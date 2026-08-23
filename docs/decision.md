# Decision Log — Retail Sales Intelligence Pipeline

Format: [ID] Date | Decision | Why | Alternatives considered

---

## Phase 0 — Environment & Architecture

**D001** | 2026-08-12 | Warehouse: Postgres (local, Docker) as primary target; dbt project designed for multi-target (Postgres + optional Snowflake later) | Free, no trial expiration, faster local iteration while learning dbt/SQL concepts; avoids network latency masking modeling mistakes; multi-target design still allows adding Snowflake later without remodeling | Snowflake-first (rejected: trial time/credit pressure during the learning phase, worse for iterating on dbt models quickly)

**D002** | 2026-08-12 | Orchestration: Airflow via Astro CLI on WSL2 + Docker Desktop | Airflow isn't officially supported natively on Windows; Astro CLI wraps the standard Airflow docker-compose setup and is itself a real, resume-relevant tool used in industry | Raw docker-compose.yaml (rejected: more manual YAML maintenance for no added learning value); native Windows pip install (rejected: unsupported, known to break)

**D003** | 2026-08-12 | Python env: conda `environment.yml`, kept separate from Airflow's own containerized dependencies | environment.yml pins the interpreter version and is diffable/reviewable in git, unlike `pip freeze`; keeping Airflow's deps out of the working conda env avoids version conflicts (e.g. SQLAlchemy pin mismatches) | Single shared env for everything (rejected: high risk of dependency conflicts between Airflow's pins and general data-science packages)

**D004** | 2026-08-12 | Dataset: Olist Brazilian E-commerce dataset, no swap | Has real order-status transitions, timestamps, geolocation, reviews, and payments data — enough relational structure to justify a real star schema, and enough repeat-customer behavior to support cohort/retention SQL, which is exactly what the SQL analysis phase needs | (none — dataset was already well-suited, no serious alternative evaluated)

**D005** | 2026-08-12 | `data/raw/` is treated as immutable; no in-place edits ever | Preserves replayability — any downstream bug can be fixed by re-running from raw without worrying about which version of a file you're looking at | Editing raw files in place for convenience (rejected: destroys debuggability)

**D006** | 2026-08-23 | Environment setup: WSL2 kernel install required manual Microsoft Store route instead of `wsl --install`; Docker Desktop WSL integration required a full machine restart + `.docker/config.json` credential-store fix (`credsStore: desktop.exe` removed) to resolve a Linux/Windows credential-helper mismatch | Windows Update-based WSL kernel delivery (used on newer Windows 11 builds) doesn't ship via the legacy standalone MSI installer; Docker's default WSL credential helper is a Windows binary that WSL's Linux userspace can't execute, so it must be stripped from config.json when pulling public images without needing a credential store | (documented for reproducibility — anyone else setting this project up on Windows 11 will likely hit the same two issues)

**D007** | 2026-08-23 | Pinned dbt-core to 1.11.x and dbt-postgres to 1.10.x (not matching major.minor numbers) | dbt-core and adapter plugins (dbt-postgres, dbt-snowflake, etc.) are released independently and don't share version numbers — dbt Labs publishes an official "compatible track" pairing specific core/adapter versions together. Initially assumed dbt-postgres would match dbt-core's version number (1.12), which doesn't exist yet for the postgres adapter; verified the actual compatible pairing before pinning | (none — lesson: check the adapter's own release history / dbt's compatible-track docs before pinning, don't assume adapter and core versions move together)

## Phase 1 — Data Ingestion

**D008** | 2026-08-23 | Ingestion source: Kaggle API (`kaggle` Python client + kaggle.json credentials) rather than manual CSV download | Scriptable and repeatable — the same command works locally and later inside an Airflow task, with no manual browser step in the loop. Credentials stored outside the repo in the user profile, never committed | Manual download (rejected: not automatable, breaks the "Airflow runs this on a schedule" requirement for Phase 2)

**D009** | 2026-08-23 | Validation checks schema (expected columns present) + row count floor + null-percentage audit (informational, not blocking) per file, not a single blanket check | Per-file validation gives an exact failure point instead of a vague "something's wrong"; nulls are reported rather than failed-on because null presence alone doesn't indicate a problem (e.g. undelivered orders legitimately have null delivery dates) — severity requires business context we don't have yet at ingestion time | A single dataset-wide validation function (rejected: harder to pinpoint which file/column actually failed)

**D010** | 2026-08-23 | Added `raw_files_already_valid()` skip-check before download, for idempotent re-runs | Makes ingestion safe to re-run without re-downloading unchanged data every time — important once Airflow schedules this daily in Phase 2 | Always re-download (rejected: wasteful, and a bad orchestration pattern)

**D011** | 2026-08-23 | Added `pytest.ini` with `pythonpath = .` at project root | pytest doesn't automatically add the project root to sys.path the way `python -m` does, so `from scripts.ingestion...` imports failed during test collection despite working fine when running the script directly. `pythonpath = .` (pytest 7.0+ built-in setting) fixes this without needing a manual `conftest.py` sys.path hack | manual `sys.path.insert()` in each test file (rejected: repetitive, easy to forget in new test files, less standard than pytest's built-in config option)