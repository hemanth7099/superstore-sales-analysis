"""Clean and analyze the Sample Superstore retail dataset.

Run from the repository root:
    python src/analyze.py
Or specify a CSV path:
    python src/analyze.py --input "data/raw/Sample - Superstore Sales (Excel).csv"

Outputs include cleaned data, KPI/quality tables, summary tables, and charts.
Missing values are reported, not silently imputed.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Save charts without opening desktop windows.
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "Sample - Superstore Sales (Excel).csv"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "outputs" / "figures"
TABLES_DIR = ROOT / "outputs" / "tables"
SUMMARY_PATH = ROOT / "outputs" / "analysis_summary.md"


def normalize_header(value: object) -> str:
    """Convert headers such as 'Sub-Category' and 'Order Date' to snake_case."""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def load_csv(path: Path) -> pd.DataFrame:
    """Load CSV while trying common encodings used by public sample datasets."""
    errors: list[str] = []
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise ValueError("Could not decode the CSV. Tried: " + "; ".join(errors))


def choose_input(requested: str | None) -> Path:
    if requested:
        path = Path(requested).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")
        return path

    if DEFAULT_INPUT.exists():
        return DEFAULT_INPUT

    candidates = sorted((ROOT / "data" / "raw").glob("*.csv"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        names = "\n".join(f"  - {p.name}" for p in candidates)
        raise FileNotFoundError(
            "More than one CSV is in data/raw. Specify one with --input:\n" + names
        )
    raise FileNotFoundError(
        "Dataset not found. Download the Sample Superstore CSV, place it in "
        f"{ROOT / 'data' / 'raw'}, and name it 'Sample - Superstore Sales (Excel).csv'. "
        "See the Dataset section in README.md."
    )


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object], list[str]]:
    """Normalize columns, clean types and derive analysis fields.

    Blank cells are treated as missing. Exact duplicates are removed. Missing
    values are otherwise preserved and documented rather than guessed/imputed.
    """
    df = raw.copy()
    original_rows = len(df)
    df.columns = [normalize_header(col) for col in df.columns]

    # Trim text values and convert whitespace-only strings to missing values.
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        df[col] = df[col].replace(r"^\s*$", pd.NA, regex=True)

    source_columns = list(df.columns)
    missing_before = int(df[source_columns].isna().sum().sum())
    duplicates = int(df.duplicated().sum())
    if duplicates:
        df = df.drop_duplicates().copy()

    # Convert numeric fields when present. Any unparseable values become NA,
    # so they will be reported in the missing-value table instead of hidden.
    numeric_columns = [
        "sales", "profit", "quantity", "discount", "product_base_margin", "shipping_cost"
    ]
    for col in numeric_columns:
        if col in df.columns:
            cleaned = df[col].astype("string").str.replace(r"[$,]", "", regex=True)
            df[col] = pd.to_numeric(cleaned, errors="coerce")

    for col in ("order_date", "ship_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    required_for_analysis = ["sales", "profit"]
    missing_required = [col for col in required_for_analysis if col not in df.columns]
    if missing_required:
        raise ValueError(
            "The CSV does not contain required columns: " + ", ".join(missing_required)
            + f". Columns found: {', '.join(df.columns)}"
        )

    # Capture quality on the original/source fields only, excluding derived columns.
    missing_after_by_column = df[source_columns].isna().sum()
    missing_after = int(missing_after_by_column.sum())
    nonzero_missing = missing_after_by_column[missing_after_by_column > 0]

    if "order_date" in df.columns:
        df["order_year"] = df["order_date"].dt.year.astype("Int64")
        df["order_month"] = df["order_date"].dt.to_period("M").astype("string")
        df["order_quarter"] = df["order_date"].dt.to_period("Q").astype("string")
    if "ship_date" in df.columns and "order_date" in df.columns:
        df["shipping_days"] = (df["ship_date"] - df["order_date"]).dt.days
    if "sales" in df.columns and "profit" in df.columns:
        df["profit_margin_pct"] = (df["profit"] / df["sales"].replace(0, pd.NA)) * 100

    quality: dict[str, object] = {
        "input_rows": original_rows,
        "duplicate_rows_removed": duplicates,
        "rows_after_deduplication": len(df),
        "missing_cells_before_cleaning": missing_before,
        "missing_cells_after_cleaning": missing_after,
        "source_columns": len(source_columns),
        "source_columns_with_missing_values": len(nonzero_missing),
    }
    return df, quality, source_columns


def save_table(df: pd.DataFrame, name: str) -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES_DIR / name, index=False)


def compact_number(value: float) -> str:
    """Format large axis values as K/M while keeping smaller figures readable."""
    value = float(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:,.0f}"


def add_value_labels(ax: plt.Axes, bars, *, horizontal: bool) -> None:
    """Add compact data labels to small/medium bar charts."""
    if len(bars) > 18:
        return
    for bar in bars:
        value = bar.get_width() if horizontal else bar.get_height()
        if pd.isna(value):
            continue
        if horizontal:
            x = bar.get_width()
            y = bar.get_y() + bar.get_height() / 2
            offset = 4 if x >= 0 else -4
            ax.annotate(
                compact_number(x), (x, y), xytext=(offset, 0),
                textcoords="offset points", va="center",
                ha="left" if x >= 0 else "right", fontsize=8,
            )
        else:
            x = bar.get_x() + bar.get_width() / 2
            y = bar.get_height()
            offset = 3 if y >= 0 else -3
            ax.annotate(
                compact_number(y), (x, y), xytext=(0, offset),
                textcoords="offset points", va="bottom" if y >= 0 else "top",
                ha="center", fontsize=8,
            )


def save_bar_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    filename: str,
    *,
    horizontal: bool = False,
    rotation: int = 0,
) -> None:
    if data.empty or x not in data.columns or y not in data.columns:
        return
    plot_data = data.dropna(subset=[x, y]).copy()
    if plot_data.empty:
        return

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, max(5.5, 0.38 * len(plot_data)) if horizontal else 6))
    if horizontal:
        plot_data = plot_data.sort_values(y, ascending=True)
        bars = ax.barh(plot_data[x].astype(str), plot_data[y])
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: compact_number(value)))
        ax.set_xlabel(y.replace("_", " ").title())
        ax.set_ylabel(x.replace("_", " ").title())
    else:
        bars = ax.bar(plot_data[x].astype(str), plot_data[y])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: compact_number(value)))
        ax.tick_params(axis="x", labelrotation=rotation)
        if rotation:
            for label in ax.get_xticklabels():
                label.set_horizontalalignment("right")
        ax.set_xlabel(x.replace("_", " ").title())
        ax.set_ylabel(y.replace("_", " ").title())
    ax.set_title(title, fontsize=15, pad=14)
    ax.grid(axis="x" if horizontal else "y", alpha=0.22)
    ax.set_axisbelow(True)
    add_value_labels(ax, bars, horizontal=horizontal)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_monthly_charts(monthly: pd.DataFrame) -> None:
    """Write separate, legible sales and profit trend charts."""
    if monthly.empty:
        return

    plot_data = monthly.copy()
    plot_data["month_date"] = pd.to_datetime(plot_data["order_month"] + "-01", errors="coerce")
    plot_data = plot_data.dropna(subset=["month_date"]).sort_values("month_date")
    if plot_data.empty:
        return

    # About 8–12 labels even when the dataset spans several years.
    interval = max(1, math.ceil(len(plot_data) / 10))
    for metric, title, filename in (
        ("sales", "Monthly Sales Trend", "monthly_sales_trend.png"),
        ("profit", "Monthly Profit Trend", "monthly_profit_trend.png"),
    ):
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(plot_data["month_date"], plot_data[metric], marker="o", markersize=3.5, linewidth=1.8)
        ax.set_title(title, fontsize=15, pad=14)
        ax.set_xlabel("Order month")
        ax.set_ylabel(metric.title())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: compact_number(value)))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.tick_params(axis="x", labelrotation=35)
        ax.grid(axis="y", alpha=0.22)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / filename, dpi=200, bbox_inches="tight")
        plt.close(fig)

    # Remove the old combined-scale chart so users don't mistake it for the updated one.
    legacy = FIGURES_DIR / "monthly_sales_profit_trend.png"
    if legacy.exists():
        legacy.unlink()


def create_outputs(
    df: pd.DataFrame,
    quality: dict[str, object],
    input_path: Path,
    source_columns: list[str],
) -> dict[str, float | int | str]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / "superstore_clean.csv", index=False)

    # Write a specific missing-values report for source columns, not derived fields.
    missing_counts = df[source_columns].isna().sum()
    missing_counts = missing_counts[missing_counts > 0]
    missing_report = pd.DataFrame(
        {
            "column": missing_counts.index.astype(str),
            "missing_count": missing_counts.values.astype(int),
            "percent_of_rows": [
                round(int(count) / len(df) * 100, 2) if len(df) else 0.0
                for count in missing_counts.values
            ],
            "treatment": "Preserved as missing; no imputation applied",
        }
    )
    if missing_report.empty:
        missing_report = pd.DataFrame(
            columns=["column", "missing_count", "percent_of_rows", "treatment"]
        )
    save_table(missing_report, "missing_values_by_column.csv")

    total_sales = float(df["sales"].fillna(0).sum())
    total_profit = float(df["profit"].fillna(0).sum())
    transaction_count = int(df["order_id"].nunique()) if "order_id" in df.columns else int(len(df))
    customer_col = "customer_id" if "customer_id" in df.columns else (
        "customer_name" if "customer_name" in df.columns else None
    )
    customer_count = int(df[customer_col].nunique()) if customer_col else 0
    margin = (total_profit / total_sales * 100) if total_sales else 0.0
    avg_order_value = (total_sales / transaction_count) if transaction_count else 0.0

    kpis = pd.DataFrame([
        {"metric": "rows_analyzed", "value": int(len(df))},
        {"metric": "unique_orders", "value": transaction_count},
        {"metric": "unique_customers", "value": customer_count},
        {"metric": "total_sales", "value": round(total_sales, 2)},
        {"metric": "total_profit", "value": round(total_profit, 2)},
        {"metric": "overall_profit_margin_pct", "value": round(margin, 2)},
        {"metric": "average_sales_per_order", "value": round(avg_order_value, 2)},
        {"metric": "duplicate_rows_removed", "value": int(quality["duplicate_rows_removed"])},
        {"metric": "missing_cells_after_cleaning", "value": int(quality["missing_cells_after_cleaning"])},
    ])
    save_table(kpis, "kpis.csv")
    save_table(pd.DataFrame([quality]), "data_quality.csv")

    monthly = pd.DataFrame()
    if "order_month" in df.columns:
        monthly = df.dropna(subset=["order_month"]).groupby("order_month", as_index=False).agg(
            sales=("sales", "sum"), profit=("profit", "sum")
        ).sort_values("order_month")
        save_table(monthly, "monthly_sales_profit.csv")
        save_monthly_charts(monthly)

    region = pd.DataFrame()
    if "region" in df.columns:
        region = df.groupby("region", dropna=False, as_index=False).agg(
            sales=("sales", "sum"), profit=("profit", "sum")
        ).sort_values("sales", ascending=False)
        save_table(region, "region_performance.csv")
        save_bar_chart(region, "region", "sales", "Sales by Region", "sales_by_region.png", horizontal=True)
        save_bar_chart(region, "region", "profit", "Profit by Region", "profit_by_region.png", horizontal=True)

    category = pd.DataFrame()
    if "category" in df.columns:
        category = df.groupby("category", dropna=False, as_index=False).agg(
            sales=("sales", "sum"), profit=("profit", "sum")
        ).sort_values("sales", ascending=False)
        save_table(category, "category_performance.csv")
        save_bar_chart(category, "category", "sales", "Sales by Product Category", "sales_by_category.png")
        save_bar_chart(category, "category", "profit", "Profit by Product Category", "profit_by_category.png")

    subcategory = pd.DataFrame()
    if "sub_category" in df.columns:
        subcategory = df.groupby("sub_category", dropna=False, as_index=False).agg(
            sales=("sales", "sum"), profit=("profit", "sum")
        ).sort_values("profit", ascending=True)
        save_table(subcategory, "subcategory_performance.csv")
        save_bar_chart(
            subcategory, "sub_category", "profit", "Profit by Sub-Category",
            "profit_by_subcategory.png", horizontal=True,
        )

    if "segment" in df.columns:
        segment = df.groupby("segment", dropna=False, as_index=False).agg(
            sales=("sales", "sum"), profit=("profit", "sum")
        ).sort_values("sales", ascending=False)
        save_table(segment, "segment_performance.csv")

    if "product_name" in df.columns:
        top_products = df.groupby("product_name", as_index=False).agg(
            sales=("sales", "sum"), profit=("profit", "sum")
        ).sort_values("sales", ascending=False).head(10)
        save_table(top_products, "top_10_products_by_sales.csv")

    if "customer_name" in df.columns:
        top_customers = df.groupby("customer_name", as_index=False).agg(
            sales=("sales", "sum"), profit=("profit", "sum")
        ).sort_values("sales", ascending=False).head(10)
        save_table(top_customers, "top_10_customers_by_sales.csv")

    corr: float | None = None
    if {"discount", "profit"}.issubset(df.columns):
        scatter = df.dropna(subset=["discount", "profit"])
        if not scatter.empty:
            corr_value = scatter["discount"].corr(scatter["profit"])
            corr = float(corr_value) if pd.notna(corr_value) else None
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.scatter(
                scatter["discount"], scatter["profit"],
                s=18, alpha=0.22, edgecolors="none", rasterized=True,
            )
            ax.axhline(0, linewidth=1, linestyle="--", alpha=0.7)
            corr_text = f"Pearson r = {corr:.3f}" if corr is not None else "Correlation unavailable"
            ax.set_title(f"Discount vs. Profit ({corr_text}; association only)", fontsize=13, pad=14)
            ax.set_xlabel("Discount")
            ax.set_ylabel("Profit")
            ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
            ax.grid(alpha=0.15)
            ax.set_axisbelow(True)
            fig.tight_layout()
            fig.savefig(FIGURES_DIR / "discount_vs_profit.png", dpi=200, bbox_inches="tight")
            plt.close(fig)

    # Build a concise, data-driven summary. Findings are calculated from this input CSV.
    lines = [
        "# Superstore Sales Analysis — Generated Summary",
        "",
        f"**Input file:** `{input_path.name}`",
        f"**Rows analyzed:** {len(df):,}",
        f"**Unique orders:** {transaction_count:,}",
        f"**Unique customers:** {customer_count:,}" if customer_col else "**Unique customers:** Not available in dataset",
        f"**Total sales:** {total_sales:,.2f}",
        f"**Total profit:** {total_profit:,.2f}",
        f"**Overall profit margin:** {margin:.2f}%",
        f"**Average sales per order:** {avg_order_value:,.2f}",
        "",
        "## Data quality checks",
        f"- Input rows: {quality['input_rows']:,}",
        f"- Exact duplicate rows removed: {quality['duplicate_rows_removed']:,}",
        f"- Missing cells before cleaning: {quality['missing_cells_before_cleaning']:,}",
        f"- Missing cells after cleaning (source columns): {quality['missing_cells_after_cleaning']:,}",
        f"- Source columns containing missing values: {quality['source_columns_with_missing_values']:,}",
        "- Missing values are preserved and documented in `outputs/tables/missing_values_by_column.csv`; no values were imputed.",
        "",
        "## Findings to review",
    ]
    if not region.empty:
        best_sales = region.sort_values("sales", ascending=False).iloc[0]
        worst_sales = region.sort_values("sales", ascending=True).iloc[0]
        best_profit = region.sort_values("profit", ascending=False).iloc[0]
        worst_profit = region.sort_values("profit", ascending=True).iloc[0]
        lines += [
            f"- Highest-sales region: **{best_sales['region']}** (sales {float(best_sales['sales']):,.2f}).",
            f"- Lowest-sales region: **{worst_sales['region']}** (sales {float(worst_sales['sales']):,.2f}).",
            f"- Highest-profit region: **{best_profit['region']}** (profit {float(best_profit['profit']):,.2f}).",
            f"- Lowest-profit region: **{worst_profit['region']}** (profit {float(worst_profit['profit']):,.2f}).",
        ]
    if not category.empty:
        best = category.sort_values("profit", ascending=False).iloc[0]
        worst = category.sort_values("profit", ascending=True).iloc[0]
        lines += [
            f"- Highest-profit category: **{best['category']}** (profit {float(best['profit']):,.2f}).",
            f"- Lowest-profit category: **{worst['category']}** (profit {float(worst['profit']):,.2f}).",
        ]
    if not subcategory.empty:
        worst = subcategory.sort_values("profit", ascending=True).iloc[0]
        best = subcategory.sort_values("profit", ascending=False).iloc[0]
        lines += [
            f"- Lowest-profit sub-category: **{worst['sub_category']}** (profit {float(worst['profit']):,.2f}).",
            f"- Highest-profit sub-category: **{best['sub_category']}** (profit {float(best['profit']):,.2f}).",
        ]
    if corr is not None:
        lines += [
            f"- Correlation between discount and profit: **{corr:.3f}**. This is an association, not proof of causation."
        ]
    lines += [
        "",
        "## Outputs created",
        "- `data/processed/superstore_clean.csv` — cleaned data for further analysis.",
        "- `outputs/tables/` — KPI, data-quality, missing-value, region, category, sub-category and other summary tables.",
        "- `outputs/figures/` — charts generated from the loaded dataset, including separate monthly sales and profit trends.",
        "",
        "> This is a portfolio/learning analysis of a sample retail dataset, not a production business report. Verify the dataset provenance and permitted usage before redistributing the raw file.",
    ]
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "rows": len(df),
        "orders": transaction_count,
        "customers": customer_count,
        "sales": round(total_sales, 2),
        "profit": round(total_profit, 2),
        "margin_pct": round(margin, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean and analyze the Sample Superstore dataset.")
    parser.add_argument(
        "--input",
        help="Path to the source CSV. Defaults to data/raw/Sample - Superstore Sales (Excel).csv",
    )
    args = parser.parse_args()

    try:
        input_path = choose_input(args.input)
        print(f"Loading dataset: {input_path}")
        raw = load_csv(input_path)
        df, quality, source_columns = clean_data(raw)
        print(f"Loaded {len(raw):,} rows and {len(raw.columns):,} columns.")
        print("Creating cleaned data, summary tables, charts, and analysis_summary.md ...")
        metrics = create_outputs(df, quality, input_path, source_columns)
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("\nAnalysis complete!")
    print(f"Rows analyzed: {metrics['rows']:,}")
    print(f"Orders: {metrics['orders']:,} | Customers: {metrics['customers']:,}")
    print(
        f"Sales: {metrics['sales']:,.2f} | Profit: {metrics['profit']:,.2f} "
        f"| Profit margin: {metrics['margin_pct']:.2f}%"
    )
    print(f"Summary: {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Charts: {FIGURES_DIR.relative_to(ROOT)}")
    print(f"Tables: {TABLES_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
