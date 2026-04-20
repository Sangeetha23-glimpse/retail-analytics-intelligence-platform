-- ============================================================
--  RETAIL ANALYTICS PLATFORM  |  MySQL 8.0+
--  Dataset : Superstore train.csv
--  Rows    : 9,800   |  Customers : 793  |  Products : 1,861
--  Revenue : $2,261,537  |  Period : Jan 2015 – Dec 2018
-- ============================================================

CREATE DATABASE IF NOT EXISTS retail_analytics
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE retail_analytics;

-- ── DIMENSION: CUSTOMERS (793 rows) ──────────────────────────
DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers (
    customer_id    VARCHAR(20)   NOT NULL,
    customer_name  VARCHAR(50)   NOT NULL,
    segment        VARCHAR(20)   NOT NULL,   -- Consumer | Corporate | Home Office
    country        VARCHAR(50)   NOT NULL,
    city           VARCHAR(30)   NOT NULL,
    state          VARCHAR(50)   NOT NULL,
    postal_code    VARCHAR(10)   DEFAULT '00000',  -- 11 NULLs in source data
    region         VARCHAR(20)   NOT NULL,          -- West | East | Central | South
    PRIMARY KEY (customer_id)
) ENGINE=InnoDB;

-- ── DIMENSION: PRODUCTS (1,861 rows) ─────────────────────────
DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    product_id     VARCHAR(30)   NOT NULL,
    product_name   VARCHAR(200)  NOT NULL,   -- max 127 chars in dataset
    category       VARCHAR(30)   NOT NULL,   -- Furniture | Office Supplies | Technology
    sub_category   VARCHAR(30)   NOT NULL,   -- 17 distinct values
    PRIMARY KEY (product_id)
) ENGINE=InnoDB;

-- ── FACT: ORDERS (9,800 rows) ────────────────────────────────
DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders (
    row_id          INT            NOT NULL,
    order_id        VARCHAR(20)    NOT NULL,
    order_date      DATE           NOT NULL,
    ship_date       DATE           NOT NULL,
    ship_mode       VARCHAR(20)    NOT NULL,  -- Standard Class | Second Class | First Class | Same Day
    customer_id     VARCHAR(20)    NOT NULL,
    product_id      VARCHAR(30)    NOT NULL,
    sales           DECIMAL(12,4)  NOT NULL,  -- max $22,638.48
    -- Computed columns (MySQL 5.7+)
    delivery_days   INT            AS (DATEDIFF(ship_date, order_date)) STORED,
    is_delayed      TINYINT(1)     AS (IF(DATEDIFF(ship_date, order_date) > 5, 1, 0)) STORED,
    PRIMARY KEY (row_id),
    KEY idx_order_id    (order_id),
    KEY idx_order_date  (order_date),
    KEY idx_customer    (customer_id),
    KEY idx_product     (product_id),
    KEY idx_ship_mode   (ship_mode),
    KEY idx_delayed     (is_delayed),
    CONSTRAINT fk_customer FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
    CONSTRAINT fk_product  FOREIGN KEY (product_id)  REFERENCES dim_products(product_id)
) ENGINE=InnoDB;

-- ── VERIFICATION QUERIES ─────────────────────────────────────
-- Run after loading to confirm counts:
-- SELECT 'dim_customers' tbl, COUNT(*) cnt FROM dim_customers   -- expect 793
-- UNION ALL
-- SELECT 'dim_products',      COUNT(*)     FROM dim_products     -- expect 1861
-- UNION ALL
-- SELECT 'fact_orders',       COUNT(*)     FROM fact_orders;     -- expect 9800
