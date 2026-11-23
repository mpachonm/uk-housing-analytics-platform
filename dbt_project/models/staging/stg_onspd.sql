with source as (
    select * from {{ source('bronze', 'raw_onspd') }}
),

cleaned as (
    select
        -- Space-stripped key matching stg_price_paid.postcode_clean
        regexp_replace(upper(trim(pcds)), '\s+', '', 'g') as postcode_clean,
        upper(trim(pcds)) as postcode_formatted,

        -- Parse YYYYMM strings into proper first-of-month DATE types
        try_strptime(date_introduced || '01', '%Y%m%d')::date as date_introduced,
        try_strptime(date_terminated || '01', '%Y%m%d')::date as date_terminated,
        (date_terminated is null or trim(date_terminated) = '') as is_active_postcode,

        -- Official GSS Geographic Codes
        nullif(trim(country_code), '') as country_code,
        nullif(trim(region_code), '') as region_code,
        nullif(trim(county_code), '') as county_code,
        nullif(trim(local_authority_code), '') as local_authority_code,
        nullif(trim(ward_code), '') as ward_code,

        -- Map official ONS Country GSS codes to readable names
        case trim(country_code)
            when 'E92000001' then 'England'
            when 'W92000004' then 'Wales'
            when 'S92000003' then 'Scotland'
            when 'N92000002' then 'Northern Ireland'
            when 'L93000001' then 'Channel Islands'
            when 'M83000003' then 'Isle of Man'
            else 'Other/Unknown'
        end as country_name,

        -- Map official ONS English Region GSS codes to readable names
        case trim(region_code)
            when 'E12000001' then 'North East'
            when 'E12000002' then 'North West'
            when 'E12000003' then 'Yorkshire and The Humber'
            when 'E12000004' then 'East Midlands'
            when 'E12000005' then 'West Midlands'
            when 'E12000006' then 'East of England'
            when 'E12000007' then 'London'
            when 'E12000008' then 'South East'
            when 'E12000009' then 'South West'
            when 'W99999999' then 'Wales'
            when 'S99999999' then 'Scotland'
            when 'N99999999' then 'Northern Ireland'
            else 'Other/Channel Islands/IoM'
        end as region_name,

        latitude,
        longitude,

        -- Lineage metadata
        _loaded_at,
        _source_file
    from source
    where pcds is not null
)

select * from cleaned