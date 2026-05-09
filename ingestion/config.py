"""Centralized configuration loaded from environment variables."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class PostgresConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    db: str = os.getenv("POSTGRES_DB", "analytics")
    user: str = os.getenv("POSTGRES_USER", "analytics_user")
    password: str = os.getenv("POSTGRES_PASSWORD", "change_me")

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )


@dataclass(frozen=True)
class BigQueryConfig:
    project_id: str = os.getenv("GCP_PROJECT_ID", "")
    dataset: str = os.getenv("BQ_DATASET", "product_analytics")
    credentials_path: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")


@dataclass(frozen=True)
class DataConfig:
    raw_csv_path: str = os.getenv("RAW_CSV_PATH", "./data/events.csv")


PG = PostgresConfig()
BQ = BigQueryConfig()
DATA = DataConfig()
