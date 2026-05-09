"""
Export dashboard query results to parquet files for Streamlit Cloud demo mode.

Run once against local Postgres (port 5433) after a successful dbt run:
    python dashboard/data_export.py

Produces dashboard/data/*.parquet — commit these files so the deployed app
can run without a database connection.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER',     'analytics_user')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'analytics_pw')}@"
    f"{os.getenv('POSTGRES_HOST',     'localhost')}:"
    f"{os.getenv('POSTGRES_PORT',     '5433')}/"
    f"{os.getenv('POSTGRES_DB',       'analytics')}"
)

STAGING      = "staging"
INTERMEDIATE = "intermediate"
MARTS        = "marts"

OUT_DIR = Path(__file__).parent / "data"


def export_all() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    queries: dict[str, str] = {
        "kpi_summary": f"""
            SELECT
                COUNT(DISTINCT user_id)                                          AS users,
                COUNT(DISTINCT session_id)                                       AS sessions,
                COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END) AS buyers,
                COALESCE(SUM(CASE WHEN event_type='purchase' THEN price END), 0) AS gmv,
                COUNT(*)                                                         AS events
            FROM {STAGING}.stg_events
        """,

        "funnel": f"""
            SELECT stage, stage_order, users, pct_of_top, pct_of_prev
            FROM {MARTS}.funnel
            ORDER BY stage_order
        """,

        "retention": f"""
            SELECT cohort_week, week_number, retention_rate, cohort_users
            FROM {MARTS}.retention
            ORDER BY cohort_week, week_number
        """,

        "daily_activity": f"""
            SELECT DATE_TRUNC('day', event_at)::date                                   AS day,
                   COUNT(DISTINCT user_id)                                              AS dau,
                   COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END)    AS buyers,
                   COUNT(*)                                                             AS events,
                   COALESCE(SUM(CASE WHEN event_type='purchase' THEN price END), 0)    AS gmv
            FROM {STAGING}.stg_events
            GROUP BY 1
            ORDER BY 1
        """,

        "top_categories": f"""
            SELECT COALESCE(category_code, 'unknown') AS category,
                   COUNT(*)                            AS purchases,
                   SUM(price)                          AS revenue,
                   COUNT(DISTINCT user_id)             AS buyers
            FROM {STAGING}.stg_events
            WHERE event_type = 'purchase'
            GROUP BY 1
            ORDER BY revenue DESC
            LIMIT 15
        """,
    }

    total_bytes = 0
    with engine.connect() as conn:
        for name, sql in queries.items():
            df = pd.read_sql(text(sql.strip()), conn)
            path = OUT_DIR / f"{name}.parquet"
            df.to_parquet(path, index=False)
            size = path.stat().st_size
            total_bytes += size
            print(f"  {name:20s}  {len(df):6,} rows  {size/1024:6.1f} KB  →  {path.name}")

    print(f"\nTotal: {total_bytes/1024:.1f} KB across {len(queries)} files")
    print(f"Output dir: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    export_all()
