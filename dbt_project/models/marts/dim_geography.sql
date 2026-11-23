with postcode_history as (
    select
        md5(postcode_clean || '|' || cast(dbt_valid_from as varchar)) as geography_sk,
        postcode_clean,
        postcode_formatted,
        country_code,
        country_name,
        region_code,
        region_name,
        county_code,
        local_authority_code,
        ward_code,
        latitude,
        longitude,
        is_active_postcode,
        date_introduced,
        date_terminated,
        cast(dbt_valid_from as timestamp) as valid_from,
        cast(dbt_valid_to as timestamp) as valid_to,
        (dbt_valid_to is null) as is_current_record
    from {{ ref('snap_postcodes') }}
),

unknown_member as (
    select
        '-1' as geography_sk,
        'UNKNOWN' as postcode_clean,
        'UNKNOWN' as postcode_formatted,
        'UNKNOWN' as country_code,
        'Unknown' as country_name,
        'UNKNOWN' as region_code,
        'Unknown' as region_name,
        'UNKNOWN' as county_code,
        'UNKNOWN' as local_authority_code,
        'UNKNOWN' as ward_code,
        cast(null as double) as latitude,
        cast(null as double) as longitude,
        false as is_active_postcode,
        cast(null as date) as date_introduced,
        cast(null as date) as date_terminated,
        cast('1900-01-01' as timestamp) as valid_from,
        cast(null as timestamp) as valid_to,
        true as is_current_record
)

select * from postcode_history
union all
select * from unknown_member