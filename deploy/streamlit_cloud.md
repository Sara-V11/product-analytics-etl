# Deploying to Streamlit Community Cloud

The dashboard runs in two modes:

| Mode | Trigger | Data source |
|---|---|---|
| **Live DB** | `POSTGRES_HOST` env var set | Queries run against Postgres in real time |
| **Demo mode** | `POSTGRES_HOST` not set (default on Streamlit Cloud) | Reads `dashboard/data/*.parquet` snapshots |

---

## Streamlit Cloud app settings

When you create the app on [share.streamlit.io](https://share.streamlit.io), set this
field exactly:

| Setting | Value |
|---|---|
| **Main file path** | `dashboard/app.py` |

Streamlit Cloud auto-detects `requirements.txt` at the repo root — no need to specify
a custom path in Advanced settings.

**Requirements file layout**

| File | Used by | Contents |
|---|---|---|
| `requirements.txt` | Streamlit Cloud | 7 slim dashboard deps (Streamlit, Plotly, pandas, pyarrow, …) |
| `requirements-dashboard.txt` | Docker dashboard container | Same 7 deps + psycopg2-binary for live DB access |
| `docker/airflow/Dockerfile` | Airflow containers | dbt-core, dbt-postgres, python-dotenv — installed directly in the image |

Streamlit Cloud runs in a sandboxed environment with no Docker and no Postgres, so its
`requirements.txt` deliberately omits psycopg2 (no DB to connect to) and all Airflow/dbt
deps (they would time out the build). The Docker containers use their own separate dep
files because their runtime needs are different.

**Why not a proxy `streamlit_app.py` at root?**
Streamlit Cloud's "Main file path" field accepts any path in the repo — no entry-point
shim at root is needed. A shim would add an indirection layer for no benefit.

---

## Step 1 — Export parquet snapshots (run once locally)

With the Docker stack running (`docker compose up -d`):

```bash
pip install -r requirements.txt

python dashboard/data_export.py
```

Expected output (~6 files, total < 5 MB):
```
kpi_summary          1 rows     1.5 KB  →  kpi_summary.parquet
funnel               3 rows     3.2 KB  →  funnel.parquet
retention           15 rows     3.4 KB  →  retention.parquet
cohort          184,805 rows  2804.3 KB  →  cohort.parquet
daily_activity      30 rows     4.4 KB  →  daily_activity.parquet
top_categories      15 rows     3.6 KB  →  top_categories.parquet
```

## Step 2 — Commit the parquet files

```bash
git add dashboard/data/
git commit -m "feat: add parquet snapshots for Streamlit Cloud demo"
```

> `dataset/` (raw CSV) is gitignored. `dashboard/data/` is not — the parquet
> snapshots are small and are the static data source for the deployed app.

## Step 3 — Push to GitHub

```bash
git push origin main   # or your branch
```

## Step 4 — Create the app on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **New app**.
3. Fill in:
   - **Repository**: your repo
   - **Branch**: `main`
   - **Main file path**: `dashboard/app.py`
4. Click **Advanced settings**:
   - **Secrets**: leave empty (no DB credentials needed for demo mode)
5. Click **Deploy**.

The app starts in demo mode automatically because `POSTGRES_HOST` is not set.

## Step 5 — Verify demo mode locally before pushing

```bash
POSTGRES_HOST="" streamlit run dashboard/app.py
```

The header badge should read **Demo mode** and all five KPI cards and four tabs should
show the same numbers as the live DB.

---

## Refreshing the snapshots

Re-run `python dashboard/data_export.py` whenever the underlying data changes (new DAG run,
schema change, etc.), then commit and push. Streamlit Cloud redeploys automatically on push.

## Connecting a live database (optional)

To point the deployed app at a real Postgres instance, add these secrets in the Streamlit
Cloud dashboard (Settings → Secrets):

```toml
POSTGRES_HOST     = "your-db-host"
POSTGRES_PORT     = "5432"
POSTGRES_USER     = "analytics_user"
POSTGRES_PASSWORD = "your-password"
POSTGRES_DB       = "analytics"
```

The `USE_LIVE_DB` flag flips to `True` and queries run against the live DB instead of
the parquet files.
