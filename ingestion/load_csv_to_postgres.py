"""
Load raw Kaggle clickstream CSV into PostgreSQL via COPY FROM STDIN.

Steps:
  1. verify_columns() — peek 5 rows, confirm COLUMN_MAP alignment before full run
  2. ensure_table()   — CREATE TABLE IF NOT EXISTS + indexes
  3. load_csv()       — chunked CSV read → COPY each chunk via copy_expert

COPY is 10–50× faster than pandas to_sql / multi-row INSERT for bulk loads.
"""
from __future__ import annotations

import logging
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from config import DATA, PG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)

CHUNK_SIZE = 200_000   # larger chunks amortise per-COPY overhead vs to_sql
TABLE_NAME = "events_raw"

COLUMN_MAP = {
    "event_time":    "event_time",
    "event_type":    "event_type",
    "product_id":    "product_id",
    "category_id":   "category_id",
    "category_code": "category_code",
    "brand":         "brand",
    "price":         "price",
    "user_id":       "user_id",
    "user_session":  "user_session",
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events_raw (
    event_time      TIMESTAMP,
    event_type      TEXT,
    product_id      BIGINT,
    category_id     BIGINT,
    category_code   TEXT,
    brand           TEXT,
    price           NUMERIC(10, 2),
    user_id         BIGINT,
    user_session    TEXT,
    ingested_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_raw_user      ON events_raw(user_id);
CREATE INDEX IF NOT EXISTS idx_events_raw_session   ON events_raw(user_session);
CREATE INDEX IF NOT EXISTS idx_events_raw_time      ON events_raw(event_time);
CREATE INDEX IF NOT EXISTS idx_events_raw_type      ON events_raw(event_type);
"""


def ensure_table(engine) -> None:
    """Create raw events table + indexes if they don't already exist."""
    log.info("Ensuring target table exists: %s", TABLE_NAME)
    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))


def verify_columns(csv_path: Path) -> dict[str, str]:
    """Peek at 5 rows and confirm COLUMN_MAP alignment before full ingest.

    Returns the subset of COLUMN_MAP whose source columns are present in the CSV.
    Raises ValueError if nothing matches (catches header mismatches early).
    """
    sample  = pd.read_csv(csv_path, nrows=5)
    present = {src: dst for src, dst in COLUMN_MAP.items() if src in sample.columns}
    missing = [s for s in COLUMN_MAP if s not in sample.columns]
    extra   = [c for c in sample.columns if c not in COLUMN_MAP]

    log.info("CSV header columns  : %s", list(sample.columns))
    log.info("Mapped to Postgres  : %s → %s",
             list(present.keys()), list(present.values()))
    if missing:
        log.warning("In COLUMN_MAP but missing from CSV (skipped): %s", missing)
    if extra:
        log.info("In CSV but not in COLUMN_MAP (dropped)        : %s", extra)
    if not present:
        raise ValueError(
            f"No columns in {csv_path} matched COLUMN_MAP — verify CSV headers."
        )

    log.info("Column check passed. %d/%d columns mapped.", len(present), len(COLUMN_MAP))
    return present


def _copy_chunk(raw_conn, df: pd.DataFrame) -> None:
    """Write one DataFrame chunk via PostgreSQL COPY FROM STDIN.

    PostgreSQL TIMESTAMP rejects the trailing ' UTC' present in the Kaggle CSV,
    so we strip it here before serialising to the in-memory buffer.
    Each chunk is committed individually so a mid-run failure leaves already-
    loaded chunks intact.
    """
    if "event_time" in df.columns:
        df = df.copy()
        df["event_time"] = df["event_time"].str.replace(" UTC", "", regex=False)

    buf = StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)

    cols = ", ".join(df.columns.tolist())
    with raw_conn.cursor() as cur:
        cur.copy_expert(
            f"COPY {TABLE_NAME} ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '')",
            buf,
        )
    raw_conn.commit()


def load_csv(csv_path: Path, engine) -> int:
    """Stream CSV in chunks into Postgres via COPY. Returns total rows loaded."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found at {csv_path}")

    col_map = verify_columns(csv_path)

    log.warning(
        "Idempotency: clearing existing rows from %s before reload (CSV path: %s)",
        TABLE_NAME, csv_path,
    )
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME}"))

    log.info("Starting COPY ingest of %s …", csv_path)

    total    = 0
    raw_conn = engine.raw_connection()
    try:
        for i, chunk in enumerate(
            pd.read_csv(csv_path, chunksize=CHUNK_SIZE), start=1
        ):
            present_srcs = [s for s in col_map if s in chunk.columns]
            chunk = chunk[present_srcs].rename(columns=col_map)
            _copy_chunk(raw_conn, chunk)
            total += len(chunk)
            log.info("Chunk %d done — running total: %d rows", i, total)
    finally:
        raw_conn.close()

    return total


def main() -> int:
    csv_path = Path(DATA.raw_csv_path)
    engine   = create_engine(PG.sqlalchemy_url)

    try:
        ensure_table(engine)
        rows = load_csv(csv_path, engine)
        log.info("✅ Done. %d rows ingested into %s", rows, TABLE_NAME)
        return 0
    except Exception:
        log.exception("❌ Ingestion failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
