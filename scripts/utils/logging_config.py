"""
Shared logging configuration for the pipeline.

Why this exists instead of print():
- print() output disappears once the terminal closes; logging can persist to a file.
- logging has severity LEVELS (DEBUG/INFO/WARNING/ERROR) so you can filter noise
  without deleting code, e.g. see everything in the log file but only WARNING+ on screen.
- logging timestamps and tags every line with which module/function produced it,
  which matters once this runs inside Airflow and you're debugging a failed task
  from a log file, not watching a live terminal.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger configured to write:
      - INFO and above to the console (so you see progress while running manually)
      - DEBUG and above to a dated file in logs/ (so you have full detail after the fact)
    """
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid attaching duplicate handlers if get_logger() is called more than once
    # for the same name (e.g. re-imported in a notebook or re-run in Airflow).
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    log_file = LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger