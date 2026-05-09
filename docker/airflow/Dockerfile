FROM apache/airflow:2.9.2-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow
# Only install packages not already provided by the apache/airflow base image.
# Do NOT reinstall sqlalchemy or pandas — Airflow 2.9.2 pins sqlalchemy==1.4.x;
# upgrading to 2.x breaks the ORM and airflow db migrate.
RUN pip install --no-cache-dir \
    python-dotenv==1.0.1 \
    dbt-core==1.8.1 \
    dbt-postgres==1.8.1
