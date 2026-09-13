"""
SQL analytics queries for the Olist Retail Analytics dashboard.
All queries accept optional bind parameters for sidebar filters:
    :start_date  (YYYY-MM-DD)
    :end_date    (YYYY-MM-DD)
    :states      — handled in Python by building an IN clause
    :categories  — handled in Python by building an IN clause
"""

# ─────────────────────────────────────────────────────────────────
# 1. Revenue + order volume by month
# ─────────────────────────────────────────────────────────────────
REVENUE_BY_MONTH = """
SELECT
    strftime('%Y-%m', o.order_purchase_timestamp) AS month,
    ROUND(SUM(oi.price), 2)                        AS revenue,
    COUNT(DISTINCT o.order_id)                     AS num_orders
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
  {state_filter}
  {cat_filter}
GROUP BY month
ORDER BY month;
"""

# ─────────────────────────────────────────────────────────────────
# 2. Top product categories by revenue (window function: running total)
# ─────────────────────────────────────────────────────────────────
TOP_CATEGORIES = """
WITH category_revenue AS (
    SELECT
        COALESCE(NULLIF(p.product_category_name,''), 'Unknown') AS category,
        ROUND(SUM(oi.price), 2)  AS revenue,
        COUNT(*)                 AS num_items_sold,
        ROUND(AVG(oi.price), 2)  AS avg_item_price
    FROM order_items oi
    JOIN products p  ON oi.product_id = p.product_id
    JOIN orders   o  ON oi.order_id   = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
      {state_filter}
    GROUP BY p.product_category_name
)
SELECT
    category,
    revenue,
    num_items_sold,
    avg_item_price,
    ROUND(SUM(revenue) OVER (ORDER BY revenue DESC), 2)    AS running_total_revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)       AS pct_of_total_revenue
FROM category_revenue
ORDER BY revenue DESC;
"""

# ─────────────────────────────────────────────────────────────────
# 3. Average delivery time by customer state
# ─────────────────────────────────────────────────────────────────
DELIVERY_TIME_BY_STATE = """
SELECT
    c.customer_state                                                         AS state,
    ROUND(AVG(julianday(o.order_delivered_customer_date)
              - julianday(o.order_purchase_timestamp)), 1)                   AS avg_delivery_days,
    COUNT(*)                                                                 AS num_delivered_orders,
    ROUND(MIN(julianday(o.order_delivered_customer_date)
              - julianday(o.order_purchase_timestamp)), 1)                   AS min_delivery_days,
    ROUND(MAX(julianday(o.order_delivered_customer_date)
              - julianday(o.order_purchase_timestamp)), 1)                   AS max_delivery_days
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
  {state_filter}
GROUP BY c.customer_state
ORDER BY avg_delivery_days DESC;
"""

# ─────────────────────────────────────────────────────────────────
# 4. Seller performance (window function: RANK)
# ─────────────────────────────────────────────────────────────────
SELLER_PERFORMANCE = """
WITH seller_revenue AS (
    SELECT
        oi.seller_id,
        s.seller_state,
        s.seller_city,
        ROUND(SUM(oi.price), 2)        AS total_revenue,
        COUNT(DISTINCT oi.order_id)    AS num_orders,
        ROUND(AVG(oi.price), 2)        AS avg_item_price
    FROM order_items oi
    JOIN sellers s ON oi.seller_id = s.seller_id
    JOIN orders  o ON oi.order_id  = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
      {state_filter}
    GROUP BY oi.seller_id, s.seller_state, s.seller_city
)
SELECT
    seller_id,
    seller_state,
    seller_city,
    total_revenue,
    num_orders,
    avg_item_price,
    RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank
FROM seller_revenue
ORDER BY revenue_rank
LIMIT 20;
"""

# ─────────────────────────────────────────────────────────────────
# 5. Review score vs delivery time
# ─────────────────────────────────────────────────────────────────
REVIEWS_VS_DELIVERY = """
SELECT
    r.review_score,
    ROUND(AVG(julianday(o.order_delivered_customer_date)
              - julianday(o.order_purchase_timestamp)), 1) AS avg_delivery_days,
    COUNT(*)                                               AS num_orders
FROM reviews r
JOIN orders o ON r.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
  {state_filter}
GROUP BY r.review_score
ORDER BY r.review_score;
"""

# ─────────────────────────────────────────────────────────────────
# 6. Order status breakdown
# ─────────────────────────────────────────────────────────────────
ORDER_STATUS_BREAKDOWN = """
SELECT
    order_status,
    COUNT(*)                                                     AS num_orders,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2)  AS pct_of_total
FROM orders
WHERE order_purchase_timestamp BETWEEN :start_date AND :end_date
GROUP BY order_status
ORDER BY num_orders DESC;
"""

# ─────────────────────────────────────────────────────────────────
# 7. Revenue + orders by customer state (for choropleth)
# ─────────────────────────────────────────────────────────────────
REVENUE_BY_STATE = """
SELECT
    c.customer_state                   AS state,
    ROUND(SUM(oi.price), 2)            AS revenue,
    COUNT(DISTINCT o.order_id)         AS num_orders,
    COUNT(DISTINCT o.customer_id)      AS num_customers
FROM orders o
JOIN customers   c  ON o.customer_id  = c.customer_id
JOIN order_items oi ON o.order_id     = oi.order_id
JOIN products    p  ON oi.product_id  = p.product_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
  {state_filter}
  {cat_filter}
GROUP BY c.customer_state
ORDER BY revenue DESC;
"""

# ─────────────────────────────────────────────────────────────────
# 8. Payment method breakdown
# ─────────────────────────────────────────────────────────────────
PAYMENT_BREAKDOWN = """
SELECT
    payment_type,
    COUNT(DISTINCT order_id)           AS num_orders,
    ROUND(SUM(payment_value), 2)       AS total_value,
    ROUND(AVG(payment_installments), 1) AS avg_installments
FROM payments
WHERE order_id IN (
    SELECT order_id FROM orders
    WHERE order_purchase_timestamp BETWEEN :start_date AND :end_date
)
GROUP BY payment_type
ORDER BY num_orders DESC;
"""

# ─────────────────────────────────────────────────────────────────
# 9. Freight vs price ratio by category
# ─────────────────────────────────────────────────────────────────
FREIGHT_RATIO_BY_CATEGORY = """
SELECT
    COALESCE(NULLIF(p.product_category_name,''), 'Unknown') AS category,
    ROUND(AVG(oi.freight_value), 2)   AS avg_freight,
    ROUND(AVG(oi.price), 2)           AS avg_price,
    ROUND(100.0 * AVG(oi.freight_value) / NULLIF(AVG(oi.price), 0), 1) AS freight_pct,
    COUNT(*)                          AS num_items
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN orders   o ON oi.order_id   = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
  {cat_filter}
GROUP BY p.product_category_name
HAVING num_items >= 30
ORDER BY freight_pct DESC
LIMIT 20;
"""

# ─────────────────────────────────────────────────────────────────
# 10. Top cities by orders
# ─────────────────────────────────────────────────────────────────
TOP_CITIES = """
SELECT
    c.customer_city                    AS city,
    c.customer_state                   AS state,
    COUNT(DISTINCT o.order_id)         AS num_orders,
    ROUND(SUM(oi.price), 2)            AS total_revenue,
    COUNT(DISTINCT o.customer_id)      AS num_customers
FROM orders o
JOIN customers   c  ON o.customer_id  = c.customer_id
JOIN order_items oi ON o.order_id     = oi.order_id
JOIN products    p  ON oi.product_id  = p.product_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
  {state_filter}
  {cat_filter}
GROUP BY c.customer_city, c.customer_state
ORDER BY num_orders DESC
LIMIT 20;
"""

# ─────────────────────────────────────────────────────────────────
# 11. Customer repeat rate
# ─────────────────────────────────────────────────────────────────
CUSTOMER_REPEAT_RATE = """
WITH order_counts AS (
    SELECT customer_id, COUNT(*) AS num_orders
    FROM orders
    WHERE order_purchase_timestamp BETWEEN :start_date AND :end_date
    GROUP BY customer_id
)
SELECT
    SUM(CASE WHEN num_orders > 1 THEN 1 ELSE 0 END)  AS repeat_customers,
    COUNT(*)                                           AS total_customers,
    ROUND(100.0 * SUM(CASE WHEN num_orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_rate_pct
FROM order_counts;
"""

# ─────────────────────────────────────────────────────────────────
# 12. Top-level KPIs
# ─────────────────────────────────────────────────────────────────
KPIS = """
SELECT
    COUNT(DISTINCT o.order_id)     AS total_orders,
    ROUND(SUM(oi.price), 2)        AS total_revenue,
    ROUND(AVG(oi.price), 2)        AS avg_item_price,
    COUNT(DISTINCT o.customer_id)  AS unique_customers
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN customers   c  ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
  {state_filter};
"""

AVG_REVIEW = """
SELECT ROUND(AVG(r.review_score), 2) AS avg_review_score
FROM reviews r
JOIN orders    o ON r.order_id   = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp BETWEEN :start_date AND :end_date
  {state_filter};
"""
