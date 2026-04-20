-- ============================================================
--  RETAIL ANALYTICS PLATFORM  |  DATA LOADING  |  MySQL 8.0+
--  Loads train.csv into retail_analytics star schema
-- ============================================================

USE retail_analytics;

-- ── STEP 1: STAGING TABLE ────────────────────────────────────
-- Temporary table to receive raw CSV before transforming
DROP TABLE IF EXISTS stg_orders;
CREATE TABLE stg_orders (
    row_id        INT,
    order_id      VARCHAR(20),
    order_date    VARCHAR(20),   -- raw string, converted in Step 3
    ship_date     VARCHAR(20),   -- raw string, converted in Step 3
    ship_mode     VARCHAR(30),
    customer_id   VARCHAR(20),
    customer_name VARCHAR(50),
    segment       VARCHAR(30),
    country       VARCHAR(50),
    city          VARCHAR(30),
    state         VARCHAR(50),
    postal_code   VARCHAR(10),
    region        VARCHAR(20),
    product_id    VARCHAR(30),
    category      VARCHAR(30),
    sub_category  VARCHAR(30),
    product_name  VARCHAR(200),
    sales         DECIMAL(12,4)
) ENGINE=InnoDB;

-- ── STEP 2: LOAD CSV ─────────────────────────────────────────
-- Option A: MySQL LOAD DATA (fastest — run from MySQL CLI as root)
-- Update the path below to match where you saved train.csv
/*
LOAD DATA LOCAL INFILE '/your/path/to/train.csv'
INTO TABLE stg_orders
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(row_id, order_id, order_date, ship_date, ship_mode,
 customer_id, customer_name, segment, country, city,
 state, @postal, region, product_id, category,
 sub_category, product_name, sales)
SET postal_code = NULLIF(@postal, '');
*/

-- Option B: MySQL Workbench → Right-click table → Table Data Import Wizard
-- Select stg_orders as destination and map all 18 columns

-- ── STEP 3: POPULATE dim_customers ───────────────────────────
INSERT IGNORE INTO dim_customers
    (customer_id, customer_name, segment, country, city, state, postal_code, region)
SELECT DISTINCT
    customer_id,
    customer_name,
    segment,
    country,
    city,
    state,
    COALESCE(postal_code, '00000'),   -- 11 NULLs replaced
    region
FROM stg_orders;

-- ── STEP 4: POPULATE dim_products ────────────────────────────
INSERT IGNORE INTO dim_products
    (product_id, product_name, category, sub_category)
SELECT DISTINCT
    product_id,
    product_name,
    category,
    sub_category
FROM stg_orders;

-- ── STEP 5: POPULATE fact_orders ─────────────────────────────
-- Dates in train.csv are DD/MM/YYYY → convert with STR_TO_DATE
INSERT INTO fact_orders
    (row_id, order_id, order_date, ship_date, ship_mode, customer_id, product_id, sales)
SELECT
    row_id,
    order_id,
    STR_TO_DATE(order_date, '%d/%m/%Y'),
    STR_TO_DATE(ship_date,  '%d/%m/%Y'),
    ship_mode,
    customer_id,
    product_id,
    sales
FROM stg_orders;

-- ── STEP 6: DROP STAGING TABLE ───────────────────────────────
DROP TABLE stg_orders;

-- ── STEP 7: VERIFY COUNTS ────────────────────────────────────
SELECT 'dim_customers' AS tbl, COUNT(*) AS cnt FROM dim_customers   -- expect 793
UNION ALL
SELECT 'dim_products',          COUNT(*)        FROM dim_products    -- expect 1861
UNION ALL
SELECT 'fact_orders',           COUNT(*)        FROM fact_orders;    -- expect 9800

-- ── STEP 8: QUICK SANITY CHECK ───────────────────────────────
SELECT
    MIN(order_date)  AS first_order,    -- expect 2015-01-03
    MAX(order_date)  AS last_order,     -- expect 2018-12-30
    SUM(sales)       AS total_sales,    -- expect ~2,261,537
    COUNT(DISTINCT customer_id) AS customers,  -- expect 793
    COUNT(DISTINCT product_id)  AS products    -- expect 1861
FROM fact_orders;
