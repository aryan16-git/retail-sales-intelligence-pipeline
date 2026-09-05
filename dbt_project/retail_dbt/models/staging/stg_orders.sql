with source as (
    select * from {{ source('raw', 'orders') }}
)

select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp::timestamp as order_purchase_at,
    order_approved_at::timestamp as order_approved_at,
    order_delivered_carrier_date::timestamp as order_delivered_carrier_at,
    order_delivered_customer_date::timestamp as order_delivered_customer_at,
    order_estimated_delivery_date::timestamp as order_estimated_delivery_at
from source