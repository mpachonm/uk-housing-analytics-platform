import os
import duckdb
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="UK Housing Market Analytics",
    page_icon="🏠",
    layout="wide",
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "uk_housing.duckdb")


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data(ttl=3600)
def load_filter_options() -> tuple[list[int], list[str]]:
    con = get_connection()
    years = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT d.calendar_year FROM main_marts.fct_property_sales f "
            "JOIN main_marts.dim_date d ON f.date_key = d.date_key ORDER BY 1"
        ).fetchall()
    ]
    regions = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT region_name FROM main_marts.dim_geography "
            "WHERE region_name NOT IN ('Unknown', 'Other/Channel Islands/IoM') ORDER BY 1"
        ).fetchall()
    ]
    return years, regions


def main() -> None:
    st.title("UK Property Market Analytics (2024–2026)")
    st.caption(
        "Powered by HM Land Registry Price Paid Data & ONS Postcode Directory | "
        "Kimball Star Schema built with dbt Core & DuckDB"
    )

    if not os.path.exists(DB_PATH):
        st.error(
            f"DuckDB warehouse not found at `{DB_PATH}`. "
            "Run `python ingestion/extract_load.py` and `dbt build` first."
        )
        st.stop()

    con = get_connection()
    years, regions = load_filter_options()

    st.sidebar.header("Filter Market Slice")
    selected_years = st.sidebar.multiselect("Transfer Year", years, default=years)
    selected_regions = st.sidebar.multiselect(
        "UK Region (leave empty for all)", regions, default=[]
    )

    if not selected_years:
        st.warning("Select at least one year in the sidebar.")
        st.stop()

    year_list = ", ".join(str(y) for y in selected_years)
    region_filter = ""
    if selected_regions:
        escaped = ", ".join("'" + r.replace("'", "''") + "'" for r in selected_regions)
        region_filter = f"AND g.region_name IN ({escaped})"

    where_clause = f"WHERE d.calendar_year IN ({year_list}) {region_filter}"

    # 1. Executive KPIs
    kpi_df = con.execute(f"""
        SELECT
            COUNT(*) AS total_sales,
            MEDIAN(f.sale_price_gbp) AS median_price,
            AVG(f.sale_price_gbp) AS avg_price,
            SUM(f.sale_price_gbp) / 1e9 AS total_volume_bn
        FROM main_marts.fct_property_sales f
        JOIN main_marts.dim_date d ON f.date_key = d.date_key
        JOIN main_marts.dim_geography g ON f.geography_sk = g.geography_sk
        {where_clause}
    """).df()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Property Sales", f"{int(kpi_df['total_sales'][0]):,}")
    c2.metric("Median Sale Price", f"£{kpi_df['median_price'][0]:,.0f}")
    c3.metric("Mean Sale Price", f"£{kpi_df['avg_price'][0]:,.0f}")
    c4.metric("Total Market Volume", f"£{kpi_df['total_volume_bn'][0]:,.1f}B")

    st.divider()

    # 2. Monthly Trend & Regional Breakdown
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Monthly Median Price Trend")
        monthly_df = con.execute(f"""
            SELECT
                d.calendar_year_month,
                COUNT(*) AS sales_count,
                MEDIAN(f.sale_price_gbp) AS median_price_gbp
            FROM main_marts.fct_property_sales f
            JOIN main_marts.dim_date d ON f.date_key = d.date_key
            JOIN main_marts.dim_geography g ON f.geography_sk = g.geography_sk
            {where_clause}
            GROUP BY d.calendar_year_month
            ORDER BY d.calendar_year_month
        """).df()

        fig_trend = px.line(
            monthly_df,
            x="calendar_year_month",
            y="median_price_gbp",
            markers=True,
            labels={
                "calendar_year_month": "Month",
                "median_price_gbp": "Median Price (£)",
            },
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_right:
        st.subheader("Median Sale Price by Region")
        region_df = con.execute(f"""
            SELECT
                g.region_name,
                COUNT(*) AS sales_count,
                MEDIAN(f.sale_price_gbp) AS median_price_gbp
            FROM main_marts.fct_property_sales f
            JOIN main_marts.dim_date d ON f.date_key = d.date_key
            JOIN main_marts.dim_geography g ON f.geography_sk = g.geography_sk
            {where_clause}
              AND g.region_name NOT IN ('Unknown', 'Other/Channel Islands/IoM')
            GROUP BY g.region_name
            ORDER BY median_price_gbp ASC
        """).df()

        fig_region = px.bar(
            region_df,
            x="median_price_gbp",
            y="region_name",
            orientation="h",
            labels={"median_price_gbp": "Median Price (£)", "region_name": "Region"},
        )
        st.plotly_chart(fig_region, use_container_width=True)

    # 3. Property Type & New Build Premium
    st.subheader("Property Type & New-Build Price Comparison")
    prop_df = con.execute(f"""
        SELECT
            p.property_type,
            p.build_status_label,
            COUNT(*) AS sales_count,
            MEDIAN(f.sale_price_gbp) AS median_price_gbp
        FROM main_marts.fct_property_sales f
        JOIN main_marts.dim_date d ON f.date_key = d.date_key
        JOIN main_marts.dim_geography g ON f.geography_sk = g.geography_sk
        JOIN main_marts.dim_property_type p ON f.property_type_sk = p.property_type_sk
        {where_clause}
          AND p.property_type != 'Other'
        GROUP BY p.property_type, p.build_status_label
        ORDER BY median_price_gbp DESC
    """).df()

    fig_prop = px.bar(
        prop_df,
        x="property_type",
        y="median_price_gbp",
        color="build_status_label",
        barmode="group",
        labels={
            "property_type": "Property Structure",
            "median_price_gbp": "Median Price (£)",
            "build_status_label": "Build Status",
        },
    )
    st.plotly_chart(fig_prop, use_container_width=True)


if __name__ == "__main__":
    main()