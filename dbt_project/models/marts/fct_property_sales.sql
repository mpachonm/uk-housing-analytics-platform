{{
    config(
        materialized='incremental',
        unique_key='transaction_id',
        incremental_strategy='delete+insert'
    )
}}

with sales as (
    select *
    from {{ ref('stg_price_paid') }}
    where
        record_status != 'D'  -- Exclude deleted deeds
    {% if is_incremental() %}
        -- 90-day lookback window catches late-reported HM Land Registry transfers
        and transfer_date >= (
            select coalesce(max(prev.transfer_date) - interval 90 day, date '2024-01-01')
            from {{ this }} as prev
        )
    {% endif %}
),

dim_geo as (
    select
        geography_sk,
        postcode_clean,
        valid_from,
        valid_to,
        is_current_record
    from {{ ref('dim_geography') }}
),

dim_prop as (
    select
        property_type_sk,
        property_type,
        tenure_type,
        is_new_build
    from {{ ref('dim_property_type') }}
)

select
    s.transaction_id,
    cast(strftime(s.transfer_date, '%Y%m%d') as integer) as date_key,
    coalesce(g.geography_sk, '-1') as geography_sk,
    p.property_type_sk,

    -- Degenerate dimensions (high-cardinality attributes kept on fact)
    s.transfer_date,
    s.postcode_formatted,
    s.town_city,
    s.district,
    s.county,
    s.transaction_category,
    s.record_status,

    -- Core measures
    s.sale_price_gbp,

    -- Audit metadata
    s._loaded_at as source_loaded_at,
    current_timestamp as dbt_updated_at

from sales as s
left join dim_geo as g
    on
        s.postcode_clean = g.postcode_clean
        and g.is_current_record = true
left join dim_prop as p
    on
        s.property_type = p.property_type
        and s.tenure_type = p.tenure_type
        and coalesce(s.is_new_build, false) = p.is_new_build
