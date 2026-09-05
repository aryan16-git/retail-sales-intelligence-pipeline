with source as (
    select * from {{ source('raw', 'geolocation') }}
)

select
    geolocation_zip_code_prefix,
    geolocation_lat::numeric as latitude,
    geolocation_lng::numeric as longitude,
    geolocation_city,
    geolocation_state
from source