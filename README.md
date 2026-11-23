# UK Housing & Geospatial Analytics Platform

An end-to-end, zero-cost Analytics Engineering platform modeling **2.38M+ UK property transactions (2024–2026)** enriched with **2.7M+ UK postcodes** using **Python, DuckDB, dbt Core, and GitHub Actions**.

## Architecture

```mermaid
flowchart LR
    A[HM Land Registry S3 CSVs] --> C[Python + DuckDB HTTPFS]
    B[ONS Postcode Directory CSV] --> C
    C -->|ZSTD Parquet| D[(Bronze Layer)]
    D --> E[dbt Staging Views]
    E --> F[dbt Snapshots - SCD Type 2]
    E --> G[dbt Marts - Kimball Star Schema]
    F --> G
    G --> H[Automated Data Quality & CI]