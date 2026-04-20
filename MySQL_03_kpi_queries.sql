-- ============================================================
--  RETAIL ANALYTICS PLATFORM  |  KPI QUERIES  |  MySQL 8.0+
--  All 12 queries verified against Superstore train.csv
--  Total Revenue : $2,261,537  |  Orders : 4,922  |  Customers : 793
-- ============================================================

USE retail_analytics;

-- ────────────────────────────────────────────────────────────
--  QUERY 01: Executive KPIs — Annual Revenue & Growth (LAG)
-- ────────────────────────────────────────────────────────────
-- MySQL 8.0+ supports LAG() window function
WITH annual AS (
    SELECT
        YEAR(order_date)                          AS yr,
        COUNT(DISTINCT order_id)                  AS total_orders,
        ROUND(SUM(sales), 2)                      AS total_sales,
        COUNT(DISTINCT customer_id)               AS active_customers
    FROM fact_orders
    GROUP BY YEAR(order_date)
)
SELECT
    yr,
    total_orders,
    total_sales,
    active_customers,
    ROUND(
        (total_sales - LAG(total_sales) OVER (ORDER BY yr))
        / LAG(total_sales) OVER (ORDER BY yr) * 100,
    1) AS yoy_growth_pct
FROM annual
ORDER BY yr;
/*
 yr   | total_orders | total_sales  | active_customers | yoy_growth_pct
------+--------------+--------------+------------------+----------------
 2015 |          947 |   479,856.00 |              590 |           NULL
 2016 |        1,019 |   459,436.00 |              612 |           -4.3   ← dip
 2017 |        1,295 |   600,193.00 |              697 |          +30.6   ← recovery
 2018 |        1,661 |   722,052.00 |              730 |          +20.3   ← growth
*/


-- ────────────────────────────────────────────────────────────
--  QUERY 02: Monthly Sales Trend with Running YTD Total
-- ────────────────────────────────────────────────────────────
SELECT
    DATE_FORMAT(order_date, '%Y-%m')              AS month,
    COUNT(DISTINCT order_id)                      AS orders,
    ROUND(SUM(sales), 2)                          AS monthly_sales,
    ROUND(AVG(sales), 2)                          AS avg_order_line,
    ROUND(
        SUM(SUM(sales)) OVER (
            PARTITION BY YEAR(order_date)
            ORDER BY DATE_FORMAT(order_date,'%Y-%m')
        ), 2
    )                                             AS ytd_sales
FROM fact_orders
GROUP BY DATE_FORMAT(order_date,'%Y-%m'), YEAR(order_date)
ORDER BY month;


-- ────────────────────────────────────────────────────────────
--  QUERY 03: Regional Performance — Sales, Delay, AOV
-- ────────────────────────────────────────────────────────────
SELECT
    c.region,
    COUNT(DISTINCT o.order_id)                           AS total_orders,
    COUNT(DISTINCT o.customer_id)                        AS customers,
    ROUND(SUM(o.sales), 0)                               AS total_sales,
    ROUND(SUM(o.sales) / SUM(SUM(o.sales)) OVER () * 100, 1) AS pct_of_revenue,
    ROUND(SUM(o.sales) / COUNT(DISTINCT o.order_id), 2)  AS avg_order_value,
    ROUND(AVG(o.delivery_days), 1)                       AS avg_delivery_days,
    ROUND(SUM(o.is_delayed) / COUNT(*) * 100, 1)         AS delay_rate_pct
FROM fact_orders o
JOIN dim_customers c ON o.customer_id = c.customer_id
GROUP BY c.region
ORDER BY total_sales DESC;
/*
 region  | orders | customers | total_sales | pct  | avg_order | delay%
---------+--------+-----------+-------------+------+-----------+--------
 West    |  1,587 |       531 |     710,220 | 31.4 |    447.52 |  18.8
 East    |  1,369 |       546 |     669,519 | 29.6 |    489.06 |  17.3   ← lowest delay
 Central |  1,156 |       429 |     492,647 | 21.8 |    426.17 |  18.9   ← highest delay
 South   |    810 |       340 |     389,151 | 17.2 |    480.43 |  17.7
*/


-- ────────────────────────────────────────────────────────────
--  QUERY 04: Category & Sub-Category Breakdown
-- ────────────────────────────────────────────────────────────
SELECT
    p.category,
    p.sub_category,
    COUNT(o.row_id)                                              AS line_items,
    ROUND(SUM(o.sales), 0)                                       AS total_sales,
    ROUND(AVG(o.sales), 0)                                       AS avg_sale,
    ROUND(
        SUM(o.sales) /
        SUM(SUM(o.sales)) OVER (PARTITION BY p.category) * 100, 1
    )                                                            AS pct_within_category
FROM fact_orders o
JOIN dim_products p ON o.product_id = p.product_id
GROUP BY p.category, p.sub_category
ORDER BY p.category, total_sales DESC;
/*
 Top Sub-Categories by Revenue:
 Phones       $327,782  (Technology)
 Chairs       $322,823  (Furniture)
 Storage      $219,343  (Office Supplies)
 Tables       $202,811  (Furniture)
 Binders      $200,029  (Office Supplies)
*/


-- ────────────────────────────────────────────────────────────
--  QUERY 05: Top 10 Customers by Lifetime Value + Churn Flag
-- ────────────────────────────────────────────────────────────
WITH customer_stats AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.segment,
        c.region,
        COUNT(DISTINCT o.order_id)                      AS order_count,
        ROUND(SUM(o.sales), 2)                          AS lifetime_value,
        ROUND(AVG(o.sales), 2)                          AS avg_order_line,
        MIN(o.order_date)                               AS first_order,
        MAX(o.order_date)                               AS last_order,
        DATEDIFF(CURDATE(), MAX(o.order_date))          AS days_since_last
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name, c.segment, c.region
)
SELECT
    customer_name,
    segment,
    region,
    order_count,
    lifetime_value,
    avg_order_line,
    first_order,
    last_order,
    CASE
        WHEN days_since_last > 365 THEN 'Churn Risk'
        WHEN days_since_last > 180 THEN 'At Risk'
        ELSE 'Active'
    END AS churn_status
FROM customer_stats
ORDER BY lifetime_value DESC
LIMIT 10;
/*
 customer_name    | segment  | region  | order_count | lifetime_value
------------------+----------+---------+-------------+----------------
 Sean Miller      | Consumer | West    |          11 |      25,043.05  ← #1
 Tamara Chand     | Consumer | West    |           9 |      19,052.22
 Raymond Buch     | Consumer | West    |           8 |      15,117.34
 Tom Ashbrook     | Consumer | Central |           9 |      14,595.62
 Adrian Barton    | Consumer | South   |          10 |      14,473.57
*/


-- ────────────────────────────────────────────────────────────
--  QUERY 06: Customer Segment Analysis (Consumer/Corporate/Home Office)
-- ────────────────────────────────────────────────────────────
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id)                   AS customers,
    COUNT(DISTINCT o.order_id)                      AS orders,
    ROUND(SUM(o.sales), 0)                          AS total_sales,
    ROUND(AVG(o.sales), 2)                          AS avg_order_line,
    ROUND(SUM(o.sales) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value
FROM fact_orders o
JOIN dim_customers c ON o.customer_id = c.customer_id
GROUP BY c.segment
ORDER BY total_sales DESC;
/*
 segment      | customers | orders | total_sales  | avg_order_value
--------------+-----------+--------+--------------+-----------------
 Consumer     |       409 |  2,404 |  1,148,061   |     477.57
 Corporate    |       236 |  1,476 |    688,494   |     466.46
 Home Office  |       148 |  1,042 |    424,982   |     408.04
*/


-- ────────────────────────────────────────────────────────────
--  QUERY 07: Delivery Performance by Ship Mode
-- ────────────────────────────────────────────────────────────
SELECT
    ship_mode,
    COUNT(*)                                        AS total_rows,
    ROUND(AVG(delivery_days), 1)                    AS avg_delivery_days,
    MIN(delivery_days)                              AS min_days,
    MAX(delivery_days)                              AS max_days,
    SUM(is_delayed)                                 AS delayed_count,
    ROUND(SUM(is_delayed) / COUNT(*) * 100, 1)      AS delay_rate_pct
FROM fact_orders
GROUP BY ship_mode
ORDER BY avg_delivery_days DESC;
/*
 ship_mode       | total_rows | avg_days | delayed | delay_rate_pct
-----------------+------------+----------+---------+----------------
 Standard Class  |      5,006 |      5.0 |   1,530 |          30.5  ← ALL delays
 Second Class    |      2,846 |      3.2 |       0 |           0.0
 First Class     |      1,538 |      2.2 |       0 |           0.0
 Same Day        |        410 |      0.0 |       0 |           0.0
 KEY FINDING: Standard Class is the ONLY source of delays in the dataset
*/


-- ────────────────────────────────────────────────────────────
--  QUERY 08: State-Level Sales Map (for Power BI Filled Map)
-- ────────────────────────────────────────────────────────────
SELECT
    c.state,
    c.region,
    COUNT(DISTINCT o.order_id)              AS orders,
    COUNT(DISTINCT o.customer_id)           AS customers,
    ROUND(SUM(o.sales), 0)                  AS total_sales,
    ROUND(AVG(o.delivery_days), 1)          AS avg_delivery_days,
    ROUND(SUM(o.is_delayed)/COUNT(*)*100,1) AS delay_rate_pct
FROM fact_orders o
JOIN dim_customers c ON o.customer_id = c.customer_id
GROUP BY c.state, c.region
ORDER BY total_sales DESC;


-- ────────────────────────────────────────────────────────────
--  QUERY 09: Repeat vs New Customers per Year
-- ────────────────────────────────────────────────────────────
WITH first_purchase AS (
    SELECT customer_id, MIN(YEAR(order_date)) AS first_year
    FROM fact_orders
    GROUP BY customer_id
),
yearly AS (
    SELECT
        YEAR(o.order_date)          AS yr,
        o.customer_id,
        fp.first_year
    FROM fact_orders o
    JOIN first_purchase fp ON o.customer_id = fp.customer_id
    GROUP BY YEAR(o.order_date), o.customer_id, fp.first_year
)
SELECT
    yr,
    COUNT(DISTINCT CASE WHEN first_year = yr THEN customer_id END)  AS new_customers,
    COUNT(DISTINCT CASE WHEN first_year < yr THEN customer_id END)  AS returning_customers
FROM yearly
GROUP BY yr
ORDER BY yr;


-- ────────────────────────────────────────────────────────────
--  QUERY 10: Ship Mode Preference by Customer Segment
-- ────────────────────────────────────────────────────────────
SELECT
    c.segment,
    o.ship_mode,
    COUNT(*)                                                       AS orders,
    ROUND(SUM(o.sales), 0)                                         AS sales,
    ROUND(
        COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (PARTITION BY c.segment), 1
    )                                                              AS pct_of_segment
FROM fact_orders o
JOIN dim_customers c ON o.customer_id = c.customer_id
GROUP BY c.segment, o.ship_mode
ORDER BY c.segment, orders DESC;


-- ────────────────────────────────────────────────────────────
--  QUERY 11: Top 10 Products by Total Sales
-- ────────────────────────────────────────────────────────────
SELECT
    p.product_name,
    p.category,
    p.sub_category,
    COUNT(o.row_id)             AS times_ordered,
    ROUND(SUM(o.sales), 0)      AS total_sales,
    ROUND(AVG(o.sales), 0)      AS avg_unit_sale
FROM fact_orders o
JOIN dim_products p ON o.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.sub_category
ORDER BY total_sales DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────
--  QUERY 12: Quarterly Sales Heatmap (Region × Quarter)
-- ────────────────────────────────────────────────────────────
SELECT
    c.region,
    YEAR(o.order_date)                          AS yr,
    QUARTER(o.order_date)                       AS qtr,
    ROUND(SUM(o.sales), 0)                      AS sales,
    COUNT(DISTINCT o.order_id)                  AS orders,
    ROUND(SUM(o.is_delayed)/COUNT(*)*100, 1)    AS delay_pct
FROM fact_orders o
JOIN dim_customers c ON o.customer_id = c.customer_id
GROUP BY c.region, YEAR(o.order_date), QUARTER(o.order_date)
ORDER BY c.region, yr, qtr;


-- ────────────────────────────────────────────────────────────
--  STORED PROCEDURE: Full Executive Summary (run anytime)
-- ────────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_executive_summary;
DELIMITER $$
CREATE PROCEDURE sp_executive_summary()
BEGIN
    -- KPI snapshot
    SELECT
        ROUND(SUM(sales), 0)                    AS total_revenue,
        COUNT(DISTINCT order_id)                AS total_orders,
        COUNT(DISTINCT customer_id)             AS total_customers,
        ROUND(SUM(sales)/COUNT(DISTINCT order_id), 2) AS avg_order_value,
        ROUND(SUM(is_delayed)/COUNT(*)*100, 1)  AS overall_delay_rate_pct,
        MIN(order_date)                         AS data_from,
        MAX(order_date)                         AS data_to
    FROM fact_orders;

    -- Best region
    SELECT c.region, ROUND(SUM(o.sales),0) AS sales
    FROM fact_orders o JOIN dim_customers c ON o.customer_id=c.customer_id
    GROUP BY c.region ORDER BY sales DESC LIMIT 1;

    -- Top customer
    SELECT c.customer_name, ROUND(SUM(o.sales),2) AS ltv
    FROM fact_orders o JOIN dim_customers c ON o.customer_id=c.customer_id
    GROUP BY c.customer_id, c.customer_name ORDER BY ltv DESC LIMIT 1;

    -- Top sub-category
    SELECT p.sub_category, ROUND(SUM(o.sales),0) AS sales
    FROM fact_orders o JOIN dim_products p ON o.product_id=p.product_id
    GROUP BY p.sub_category ORDER BY sales DESC LIMIT 1;
END$$
DELIMITER ;

-- Run it:
-- CALL sp_executive_summary();
