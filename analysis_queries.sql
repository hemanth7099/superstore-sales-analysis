-- Optional SQL practice after importing data/processed/superstore_clean.csv
-- into a SQLite table named superstore_clean. Column names should be snake_case.

-- 1. Overall KPIs
SELECT
    COUNT(*) AS order_lines,
    COUNT(DISTINCT order_id) AS unique_orders,
    ROUND(SUM(sales), 2) AS total_sales,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS profit_margin_pct
FROM superstore_clean;

-- 2. Sales and profit by region
SELECT region, ROUND(SUM(sales), 2) AS sales, ROUND(SUM(profit), 2) AS profit
FROM superstore_clean
GROUP BY region
ORDER BY profit DESC;

-- 3. Category/sub-category profitability
SELECT category, sub_category,
       ROUND(SUM(sales), 2) AS sales,
       ROUND(SUM(profit), 2) AS profit,
       ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS profit_margin_pct
FROM superstore_clean
GROUP BY category, sub_category
ORDER BY profit ASC;

-- 4. Monthly trend
SELECT order_month, ROUND(SUM(sales), 2) AS sales, ROUND(SUM(profit), 2) AS profit
FROM superstore_clean
WHERE order_month IS NOT NULL
GROUP BY order_month
ORDER BY order_month;

-- 5. Discount vs profit by discount band. Treat as association, not causation.
SELECT
    CASE
        WHEN discount = 0 THEN '0%'
        WHEN discount <= 0.10 THEN '1-10%'
        WHEN discount <= 0.20 THEN '11-20%'
        WHEN discount <= 0.30 THEN '21-30%'
        ELSE 'Above 30%'
    END AS discount_band,
    COUNT(*) AS order_lines,
    ROUND(AVG(profit), 2) AS average_profit,
    ROUND(SUM(sales), 2) AS sales,
    ROUND(SUM(profit), 2) AS total_profit
FROM superstore_clean
GROUP BY discount_band
ORDER BY MIN(discount);

-- 6. Top 10 customers by sales
SELECT customer_name,
       ROUND(SUM(sales), 2) AS sales,
       ROUND(SUM(profit), 2) AS profit
FROM superstore_clean
GROUP BY customer_name
ORDER BY sales DESC
LIMIT 10;
