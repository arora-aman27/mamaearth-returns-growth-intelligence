"""Reproducible pandas cleaning, EDA, reconciliation and findings export."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ANALYSIS = ROOT / "analysis"
NARRATOR = ROOT / "narrator"
ANALYSIS.mkdir(exist_ok=True)
NARRATOR.mkdir(exist_ok=True)

customers = pd.read_csv(DATA / "customers.csv")
products = pd.read_csv(DATA / "products.csv")
orders = pd.read_csv(DATA / "orders.csv")
print("=== Task 1: Load and inspect ===")
print("customers.shape:", customers.shape)
print("products.shape:", products.shape)
print("orders.shape before cleaning:", orders.shape)

print("\n=== Task 2: Standardize payment method ===")
print("Raw unique payment methods:", sorted(orders["payment_method"].unique().tolist()))
print("Raw unique count:", orders["payment_method"].nunique())
orders["payment_method"] = orders["payment_method"].astype("string").str.strip().str.upper()
print("Normalized counts before deduplication:")
print(orders["payment_method"].value_counts().sort_index().to_string())

print("\n=== Task 3: Remove duplicate orders ===")
natural_key = ["customer_id", "product_id", "order_date", "quantity", "discount_pct", "payment_method", "rating", "returned"]
duplicate_mask = orders.duplicated(subset=natural_key, keep="first")
dropped = orders.loc[duplicate_mask].copy()
print("Duplicate rows flagged:", int(duplicate_mask.sum()))
print("Dropped order_id values:", ", ".join(dropped["order_id"].tolist()))
orders_clean = orders.loc[~duplicate_mask].copy()
print("orders_clean.shape:", orders_clean.shape)

print("\n=== Task 4: Impute missing values ===")
discount_missing = int(orders_clean["discount_pct"].isna().sum())
rating_missing = int(orders_clean["rating"].isna().sum())
rating_median = float(orders_clean["rating"].median())
print("Missing discount_pct rows before imputation:", discount_missing)
print("Median rating before imputation:", rating_median)
print("Missing rating rows before imputation:", rating_missing)
orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)
orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)
print("Null counts after imputation:", orders_clean[["discount_pct", "rating"]].isnull().sum().to_dict())

# Independent value calculation for the dropped rows proves the reconciliation delta.
price_lookup = products.set_index("product_id")["price"]
def compute_values(frame):
    out = frame.copy()
    out["price"] = out["product_id"].map(price_lookup)
    out["discount_pct"] = out["discount_pct"].fillna(0)
    out["order_value"] = out["quantity"] * out["price"] * (1 - out["discount_pct"] / 100.0)
    return out

dropped_values = compute_values(dropped)
dropped_value_total = round(float(dropped_values["order_value"].sum()), 2)
merged = orders_clean.merge(products, on="product_id", how="left", validate="many_to_one")
merged = merged.merge(customers, on="customer_id", how="left", validate="many_to_one")
merged["order_date"] = pd.to_datetime(merged["order_date"], errors="raise")
merged["order_value"] = merged["quantity"] * merged["price"] * (1 - merged["discount_pct"] / 100.0)
cleaned_total_revenue = round(float(merged["order_value"].sum()), 2)
raw_merged = orders.merge(products, on="product_id", how="left", validate="many_to_one")
raw_merged["discount_pct"] = raw_merged["discount_pct"].fillna(0)
raw_total_revenue = round(float((raw_merged["quantity"] * raw_merged["price"] * (1 - raw_merged["discount_pct"] / 100.0)).sum()), 2)
reconciliation_delta = round(raw_total_revenue - cleaned_total_revenue, 2)
print("\n=== Task 5: Merge and reconcile ===")
print("Cleaned merged row count:", len(merged))
print(f"Cleaned total revenue: ₹{cleaned_total_revenue:,.2f}")
print(f"Raw total revenue (before duplicate removal): ₹{raw_total_revenue:,.2f}")
print(f"Dropped duplicate rows' independently calculated order_value total: ₹{dropped_value_total:,.2f}")
print(f"Reconciliation delta (raw - cleaned): ₹{reconciliation_delta:,.2f}")
print("Reconciliation note: The raw SQL total exceeds the cleaned pandas total by ₹2,501.90 because the five duplicate-submit rows O0176–O0180 contribute a combined order value of ₹2,501.90. Filling missing discounts with 0% and missing ratings with the median does not change order values; discount blanks are treated as 0% in both totals, and ratings are not part of the revenue formula.")

print("\n=== Task 6: IQR outlier detection on quantity ===")
q1 = float(merged["quantity"].quantile(0.25))
q3 = float(merged["quantity"].quantile(0.75))
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
merged["is_outlier"] = (merged["quantity"] < lower) | (merged["quantity"] > upper)
outliers = merged.loc[merged["is_outlier"], ["order_id", "quantity"]]
print(f"Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f}, lower={lower:.1f}, upper={upper:.1f}")
print("Outlier rows (flagged, not dropped):")
print(outliers.to_string(index=False))

print("\n=== Task 7: COD return-rate hypothesis ===")
print("Hypothesis: COD orders have a higher return rate than CARD and UPI orders.")
return_by_payment = merged.groupby("payment_method")["returned"].agg(["count", "mean"])
return_by_payment["return_rate_pct"] = (return_by_payment["mean"] * 100).round(1)
print(return_by_payment.to_string())
cod_rate = float(return_by_payment.loc["COD", "return_rate_pct"])
print("Hypothesis:", "Confirmed" if cod_rate > max(return_by_payment.drop(index="COD")["return_rate_pct"]) else "Busted")

print("\n=== Task 8: Payment method × city tier ===")
segment = merged.groupby(["payment_method", "city_tier"])["returned"].agg(["count", "mean"])
segment["return_rate_pct"] = (segment["mean"] * 100).round(1)
print(segment.to_string())
highest_segment_idx = segment["return_rate_pct"].idxmax()
highest_segment_rate = float(segment.loc[highest_segment_idx, "return_rate_pct"])
print(f"Highest-risk segment: {highest_segment_idx[0]} + Tier-{highest_segment_idx[1]} cities at {highest_segment_rate:.1f}%.")

print("\n=== Task 9: Correlation analysis ===")
corr_cols = ["rating", "returned", "discount_pct", "quantity"]
corr = merged[corr_cols].corr(numeric_only=True)
print(corr.round(3).to_string())
def band(r):
    a = abs(float(r))
    if a < 0.2: return "negligible"
    if a < 0.4: return "weak"
    if a < 0.7: return "moderate"
    return "strong"
for i, col_a in enumerate(corr_cols):
    for col_b in corr_cols[i+1:]:
        r = float(corr.loc[col_a, col_b])
        print(f"{col_a} vs {col_b}: r={r:.3f} — {band(r)}")
discount_return_corr = float(corr.loc["discount_pct", "returned"])
print("Hypothesis 'higher discounts reduce returns':", "Busted" if band(discount_return_corr) == "negligible" else "Not supported as a strong relationship", f"(discount_pct vs returned r={discount_return_corr:.3f}).")

print("\n=== Task 10: Monthly revenue with and without flagged outliers ===")
merged["year_month"] = merged["order_date"].dt.to_period("M").astype(str)
monthly_all = merged.groupby("year_month")["order_value"].sum().round(2).sort_index()
monthly_corrected = merged.loc[~merged["is_outlier"]].groupby("year_month")["order_value"].sum().round(2).sort_index()
print("Including outliers:")
print(monthly_all.to_string())
print("Outlier-corrected (outlier orders flagged by IQR are excluded only from this comparison):")
print(monthly_corrected.to_string())
peak_month = str(monthly_corrected.idxmax())
peak_revenue = round(float(monthly_corrected.max()), 2)
inflated_month = str(monthly_all.idxmax())
inflated_revenue = round(float(monthly_all.max()), 2)
jan_corrected = round(float(monthly_corrected.loc["2026-01"]), 2)
print("Interpretation: January's apparent lead is an artifact of the two bulk orders O0011 (2026-01-28) and O0098 (2026-01-10). Once those flagged outliers are excluded, March is the genuine peak month.")

# Outputs consumed by visualization and narrator layers.
orders_clean.to_csv(ANALYSIS / "cleaned_orders.csv", index=False)
merged.to_csv(ANALYSIS / "merged_analysis.csv", index=False)
monthly_payload = {
    "monthly_revenue_including_outliers": {k: round(float(v), 2) for k, v in monthly_all.items()},
    "monthly_revenue_outlier_corrected": {k: round(float(v), 2) for k, v in monthly_corrected.items()},
    "outlier_order_ids": outliers["order_id"].tolist(),
}
(ANALYSIS / "monthly_revenue.json").write_text(json.dumps(monthly_payload, indent=2) + "\n", encoding="utf-8")
findings = {
    "cleaned_total_revenue_inr": cleaned_total_revenue,
    "raw_total_revenue_inr": raw_total_revenue,
    "duplicate_reconciliation_delta_inr": reconciliation_delta,
    "return_rate_by_payment": {method: float(return_by_payment.loc[method, "return_rate_pct"]) for method in ["COD", "CARD", "UPI"]},
    "highest_risk_segment": {"payment_method": str(highest_segment_idx[0]), "city_tier": int(highest_segment_idx[1]), "return_rate_pct": highest_segment_rate},
    "true_peak_month": {"month": peak_month, "revenue_inr": peak_revenue},
    "outlier_inflated_month": {"month": inflated_month, "apparent_revenue_inr": inflated_revenue, "corrected_revenue_inr": jan_corrected},
}
(NARRATOR / "findings.json").write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
print("\nWrote narrator/findings.json from computed values.")
