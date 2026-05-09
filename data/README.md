# Data

Place your Kaggle clickstream CSV here as `events.csv` (or update `RAW_CSV_PATH` in `.env`).

This folder is **gitignored** — never commit raw data.

## Expected schema

The ingestion script expects these columns (rename via `COLUMN_MAP` in `ingestion/load_csv_to_postgres.py` if yours differ):

- `event_time` — timestamp
- `event_type` — one of `view`, `cart`, `purchase`
- `product_id`, `category_id`, `category_code`, `brand`, `price`
- `user_id`, `user_session`

Common matching Kaggle datasets:
- *eCommerce behavior data from multi category store* (REES46)
- *eCommerce Events History in Cosmetics Shop*
