{% snapshot snap_postcodes %}

{{
    config(
      target_schema='snapshots',
      unique_key='postcode_clean',
      strategy='check',
      check_cols=[
          'is_active_postcode',
          'country_code',
          'region_code',
          'county_code',
          'local_authority_code',
          'ward_code'
      ],
      invalidate_hard_deletes=True
    )
}}

select
    postcode_clean,
    postcode_formatted,
    date_introduced,
    date_terminated,
    is_active_postcode,
    country_code,
    country_name,
    region_code,
    region_name,
    county_code,
    local_authority_code,
    ward_code,
    latitude,
    longitude,
    _loaded_at
from {{ ref('stg_onspd') }}

{% endsnapshot %}