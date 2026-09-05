with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

payments_agg as (
    -- One order can have multiple payment rows (e.g. split across a voucher +
    -- credit card). We aggregate to one row per order_id here so joining
    -- payments onto order_items (which is at a finer grain) doesn't duplicate
    -- item rows — a classic fan-out bug if done via a naive join instead.
    select
        order_id,
        sum(payment_value) as total_order_payment_value,
        count(*) as payment_count
    from {{ ref('stg_order_payments') }}
    group by order_id
)

select
    order_items.order_id,
    order_items.order_item_id,
    order_items.product_id,
    order_items.seller_id,
    orders.customer_id,
    orders.order_status,
    orders.order_purchase_at,
    orders.order_delivered_customer_at,
    order_items.price,
    order_items.freight_value,
    payments_agg.total_order_payment_value,
    payments_agg.payment_count
from order_items
left join orders
    on order_items.order_id = orders.order_id
left join payments_agg
    on order_items.order_id = payments_agg.order_id