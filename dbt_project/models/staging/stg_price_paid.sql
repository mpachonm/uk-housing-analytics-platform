with source as (
    select * from {{ source('bronze', 'raw_price_paid') }}
),

cleaned as (
    select
        -- Strip curly braces from Land Registry GUIDs for clean string joins
        trim(both '{}' from upper(trim(transaction_id))) as transaction_id,
        price as sale_price_gbp,
        cast(transfer_date as date) as transfer_date,

        -- Normalize postcodes: strip all spaces and uppercase for deterministic joins
        nullif(regexp_replace(upper(trim(postcode)), '\s+', '', 'g'), '') as postcode_clean,
        nullif(upper(trim(postcode)), '') as postcode_formatted,

        -- Decode official GOV.UK single-character codes into human-readable attributes
        case upper(trim(property_type))
            when 'D' then 'Detached'
            when 'S' then 'Semi-Detached'
            when 'T' then 'Terraced'
            when 'F' then 'Flat/Maisonette'
            when 'O' then 'Other'
            else 'Unknown'
        end as property_type,

        case upper(trim(old_new))
            when 'Y' then true
            when 'N' then false
        end as is_new_build,

        case upper(trim(duration))
            when 'F' then 'Freehold'
            when 'L' then 'Leasehold'
            else 'Unknown'
        end as tenure_type,

        -- Address components
        nullif(trim(paon), '') as primary_address_object,
        nullif(trim(saon), '') as secondary_address_object,
        nullif(trim(street), '') as street,
        nullif(trim(locality), '') as locality,
        nullif(trim(town_city), '') as town_city,
        nullif(trim(district), '') as district,
        nullif(trim(county), '') as county,

        -- Transaction category & status
        case upper(trim(ppd_category_type))
            when 'A' then 'Standard Price Paid'
            when 'B' then 'Additional Price Paid'
            else 'Unknown'
        end as transaction_category,

        upper(trim(record_status)) as record_status,

        -- Lineage metadata
        _loaded_at,
        _source_file
    from source
    where
        transaction_id is not null
        and price > 0
        and transfer_date is not null
)

select * from cleaned
