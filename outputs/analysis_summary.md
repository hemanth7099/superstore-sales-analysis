# Superstore Sales Analysis — Generated Summary

**Input file:** `Sample - Superstore Sales (Excel).csv`
**Rows analyzed:** 8,399
**Unique orders:** 5,496
**Unique customers:** 795
**Total sales:** 14,915,600.82
**Total profit:** 1,521,767.98
**Overall profit margin:** 10.20%
**Average sales per order:** 2,713.90

## Data quality checks
- Input rows: 8,399
- Exact duplicate rows removed: 0
- Missing cells before cleaning: 63
- Missing cells after cleaning (source columns): 63
- Source columns containing missing values: 1
- Missing values are preserved and documented in `outputs/tables/missing_values_by_column.csv`; no values were imputed.

## Findings to review
- Highest-sales region: **West** (sales 3,597,549.28).
- Lowest-sales region: **Nunavut** (sales 116,376.48).
- Highest-profit region: **Ontario** (profit 346,868.54).
- Lowest-profit region: **Nunavut** (profit 2,841.11).
- Correlation between discount and profit: **-0.037**. This is an association, not proof of causation.

## Outputs created
- `data/processed/superstore_clean.csv` — cleaned data for further analysis.
- `outputs/tables/` — KPI, data-quality, missing-value, region, category, sub-category and other summary tables.
- `outputs/figures/` — charts generated from the loaded dataset, including separate monthly sales and profit trends.

> This is a portfolio/learning analysis of a sample retail dataset, not a production business report. Verify the dataset provenance and permitted usage before redistributing the raw file.
