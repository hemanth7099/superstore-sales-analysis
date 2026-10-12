
# Superstore Sales & Profitability Analysis

A Python-based data analysis project exploring retail sales, profitability, regional performance, monthly trends, customers, products, and the relationship between discounts and profit.

## Project Overview

This project uses Python and Pandas to clean and analyze a sample retail sales dataset. It generates key performance indicators (KPIs), summary tables, visualizations, and a written report to help explore business performance.

## Key Results

| Metric | Result |
|---|---:|
| Rows Analyzed | 8,399 |
| Unique Orders | 5,496 |
| Unique Customers | 795 |
| Total Sales | 14,915,600.82 |
| Total Profit | 1,521,767.98 |
| Overall Profit Margin | 10.20% |
| Average Sales per Order | 2,713.90 |

## Data Visualizations

### 1. Monthly Sales Trend

![Monthly Sales Trend](outputs/figures/monthly_sales_trend.png)

### 2. Monthly Profit Trend

![Monthly Profit Trend](outputs/figures/monthly_profit_trend.png)

### 3. Sales by Region

![Sales by Region](outputs/figures/sales_by_region.png)

### 4. Profit by Region

![Profit by Region](outputs/figures/profit_by_region.png)

### 5. Discount vs. Profit

![Discount vs Profit](outputs/figures/discount_vs_profit.png)

The Pearson correlation between discount and profit is -0.037 in this dataset, indicating a very weak linear association. Correlation does not establish causation.

## Key Findings

- **Sales performance:** The West region generated the highest sales in the analyzed dataset.
- **Regional profitability:** Ontario had the highest total profit, at 346,868.54.
- **Lowest regional profit:** Nunavut had the lowest total profit, at 2,841.11.
- **Data quality:** No exact duplicate rows were found.
- **Missing values:** 63 values in `product_base_margin` were preserved as missing rather than replaced with zero.

## Tools and Technologies

- Python
- Pandas
- Matplotlib
- SQL
- Git and GitHub

## Project Structure

```text
superstore-sales-analysis/
├── README.md
├── requirements.txt
├── src/
│   └── analyze.py
├── sql/
│   └── analysis_queries.sql
└── outputs/
    ├── analysis_summary.md
    ├── figures/
    └── tables/
```

## How to Run

1. Install Python 3.11 or 3.12.
2. Download the sample dataset and place it in `data/raw/`.
3. Install dependencies:

   `pip install -r requirements.txt`

4. Run the analysis from the project root:

   `python src/analyze.py`

The script generates cleaned data, summary tables, charts, and an analysis report.

## Limitations

This is a portfolio and learning project based on a sample retail dataset. The findings describe this dataset only and should not be interpreted as proof of causal relationships. Missing product-base-margin values are documented and retained.

## Author

**Hemanth Gandhi Muppalla**

GitHub: [hemanth7099](https://github.com/hemanth7099)
