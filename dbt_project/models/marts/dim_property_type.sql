with combinations as (
    select distinct
        property_type,
        tenure_type,
        coalesce(is_new_build, false) as is_new_build
    from {{ ref('stg_price_paid') }}
)

select
    md5(property_type || '|' || tenure_type || '|' || cast(is_new_build as varchar)) as property_type_sk,
    property_type,
    tenure_type,
    is_new_build,
    case
        when is_new_build then 'New Build'
        else 'Existing / Resale'
    end as build_status_label
from combinations