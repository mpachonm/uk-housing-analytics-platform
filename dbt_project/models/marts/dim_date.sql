with date_spine as (
    select unnest(generate_series(date '2024-01-01', date '2027-12-31', interval 1 day)) as date_day
)

select
    cast(strftime(cast(date_day as date), '%Y%m%d') as integer) as date_key,
    cast(date_day as date) as date_day,
    extract(year from date_day) as calendar_year,
    extract(quarter from date_day) as calendar_quarter,
    extract(month from date_day) as calendar_month,
    strftime(date_day, '%B') as calendar_month_name,
    strftime(date_day, '%Y-%m') as calendar_year_month,
    extract(dayofweek from date_day) as day_of_week,
    strftime(date_day, '%A') as calendar_day_name,
    (extract(dayofweek from date_day) in (0, 6)) as is_weekend,
    case
        when extract(month from date_day) >= 4 then extract(year from date_day)
        else extract(year from date_day) - 1
    end as uk_fiscal_year
from date_spine
