-- Fails if any property sale has a non-positive price or a transfer date in the future
select
    transaction_id,
    transfer_date,
    sale_price_gbp
from {{ ref('fct_property_sales') }}
where
    sale_price_gbp <= 0
    or transfer_date > current_date