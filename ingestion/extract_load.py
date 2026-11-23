import glob
import os
import sys
import re
from datetime import datetime, timezone
import duckdb

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
BRONZE_DIR = os.path.join(BASE_DIR, "data", "bronze")
DB_PATH = os.path.join(BASE_DIR, "data", "uk_housing.duckdb")

# HM Land Registry Public S3 Mirror
LAND_REGISTRY_BASE_URL = (
    "http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com"
)
YEARS_TO_LOAD = [2024, 2025, 2026]


def init_duckdb() -> duckdb.DuckDBPyConnection:
    """Initialize DuckDB connection with HTTPFS support for remote CSV reads."""
    os.makedirs(BRONZE_DIR, exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    return con


def ingest_land_registry(con: duckdb.DuckDBPyConnection) -> None:
    """Stream Land Registry CSVs from S3, apply official 16-column schema, and write Bronze Parquet."""
    ppd_bronze_dir = os.path.join(BRONZE_DIR, "price_paid")
    os.makedirs(ppd_bronze_dir, exist_ok=True)
    loaded_at = datetime.now(timezone.utc).isoformat()

    for year in YEARS_TO_LOAD:
        url = f"{LAND_REGISTRY_BASE_URL}/pp-{year}.csv"
        out_parquet = os.path.join(ppd_bronze_dir, f"pp_{year}.parquet").replace("\\", "/")
        print(f"[INFO] Streaming {url} -> {out_parquet} ...")

        query = f"""
        COPY (
            SELECT
                column00 AS transaction_id,
                TRY_CAST(column01 AS BIGINT) AS price,
                TRY_CAST(column02 AS TIMESTAMP) AS transfer_date,
                column03 AS postcode,
                column04 AS property_type,
                column05 AS old_new,
                column06 AS duration,
                column07 AS paon,
                column08 AS saon,
                column09 AS street,
                column10 AS locality,
                column11 AS town_city,
                column12 AS district,
                column13 AS county,
                column14 AS ppd_category_type,
                column15 AS record_status,
                '{loaded_at}'::TIMESTAMP AS _loaded_at,
                'pp-{year}.csv' AS _source_file
            FROM read_csv(
                '{url}',
                header = false,
                delim = ',',
                quote = '"',
                escape = '"',
                all_varchar = true
            )
        ) TO '{out_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD);
        """
        con.execute(query)
        row_count = con.execute(f"SELECT COUNT(*) FROM '{out_parquet}'").fetchone()[0]
        print(f"[SUCCESS] Loaded {row_count:,} rows for {year}.")

    # Register unified Bronze view in DuckDB
    parquet_glob = os.path.join(ppd_bronze_dir, "*.parquet").replace("\\", "/")
    con.execute(f"""
        CREATE OR REPLACE VIEW bronze.raw_price_paid AS
        SELECT * FROM read_parquet('{parquet_glob}');
    """)


def ingest_onspd(con: duckdb.DuckDBPyConnection) -> None:
    """Locate the local ONSPD CSV in data/raw and convert key geographic columns to Bronze Parquet."""
    matches = glob.glob(os.path.join(RAW_DIR, "ONSPD*.csv"))
    if not matches:
        print("[ERROR] No ONSPD*.csv file found in data/raw/. Please place the extracted ONSPD CSV there.")
        sys.exit(1)

    onspd_csv = matches[0].replace("\\", "/")
    out_parquet = os.path.join(BRONZE_DIR, "onspd.parquet").replace("\\", "/")
    loaded_at = datetime.now(timezone.utc).isoformat()
    source_name = os.path.basename(onspd_csv)

    print(f"[INFO] Processing local ONSPD file: {source_name} ...")

    cols = [
        row[0]
        for row in con.execute(
            f"DESCRIBE SELECT * FROM read_csv_auto('{onspd_csv}', sample_size=10)"
        ).fetchall()
    ]

    pcd_7_col = "pcd7" if "pcd7" in cols else "pcd"
    pcd_8_col = "pcd8" if "pcd8" in cols else "pcd2"
    cty_col = next((c for c in cols if c.startswith("cty") and c.endswith("cd")), "oscty")
    lad_col = next((c for c in cols if c.startswith("lad") and c.endswith("cd")), "oslaua")
    ward_col = next((c for c in cols if re.fullmatch(r"wd\d{2}cd", c)), "osward")
    ctry_col = next((c for c in cols if c.startswith("ctry") and c.endswith("cd")), "ctry")
    rgn_col = next((c for c in cols if c.startswith("rgn") and c.endswith("cd")), "rgn")

    query = f"""
    COPY (
        SELECT
            {pcd_7_col} AS pcd,
            {pcd_8_col} AS pcd2,
            pcds,
            dointr AS date_introduced,
            doterm AS date_terminated,
            {cty_col} AS county_code,
            {lad_col} AS local_authority_code,
            {ward_col} AS ward_code,
            {ctry_col} AS country_code,
            {rgn_col} AS region_code,
            TRY_CAST(lat AS DOUBLE) AS latitude,
            TRY_CAST(long AS DOUBLE) AS longitude,
            '{loaded_at}'::TIMESTAMP AS _loaded_at,
            '{source_name}' AS _source_file
        FROM read_csv_auto('{onspd_csv}', all_varchar = true)
    ) TO '{out_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """
    con.execute(query)
    row_count = con.execute(f"SELECT COUNT(*) FROM '{out_parquet}'").fetchone()[0]
    print(f"[SUCCESS] Converted {row_count:,} postcodes to {out_parquet}.")

    con.execute(f"""
        CREATE OR REPLACE VIEW bronze.raw_onspd AS
        SELECT * FROM read_parquet('{out_parquet}');
    """)


def main() -> None:
    print("=== Starting UK Housing Bronze Ingestion ===")
    con = init_duckdb()
    try:
        ingest_land_registry(con)
        ingest_onspd(con)
        print("\n=== Bronze Ingestion Complete ===")
        print(f"DuckDB catalog ready at: {DB_PATH}")
    finally:
        con.close()


if __name__ == "__main__":
    main()