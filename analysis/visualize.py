"""Generate the two required charts from outputs of clean_and_eda.py."""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
OUT = ROOT / "visualizations"
OUT.mkdir(exist_ok=True)
merged = pd.read_csv(ANALYSIS / "merged_analysis.csv", parse_dates=["order_date"])
monthly = json.loads((ANALYSIS / "monthly_revenue.json").read_text(encoding="utf-8"))

rates = (merged.groupby("payment_method")["returned"].mean() * 100).sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(rates.index, rates.values)
for bar, value in zip(bars, rates.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f"{value:.1f}%", ha="center", va="bottom")
ax.set_ylabel("Return rate (%)")
ax.set_xlabel("Payment method")
ax.set_ylim(0, max(rates.values) * 1.18)
ax.set_title(f"COD Returns at {rates.loc['COD']:.1f}% — {rates.loc['COD']/rates.loc['CARD']:.1f}x Card")
fig.tight_layout()
fig.savefig(OUT / "return_rate_by_payment.png", dpi=160, bbox_inches="tight")
plt.close(fig)

series = pd.Series(monthly["monthly_revenue_outlier_corrected"], dtype=float).sort_index()
peak_month = series.idxmax()
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(series.index, series.values, marker="o")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (INR)")
ax.set_title(f"Outlier-Corrected Monthly Revenue — Peak: {peak_month}")
ax.tick_params(axis="x", rotation=35)
fig.tight_layout()
fig.savefig(OUT / "monthly_revenue_trend.png", dpi=160, bbox_inches="tight")
plt.close(fig)
print(f"Saved {OUT / 'return_rate_by_payment.png'}")
print(f"Saved {OUT / 'monthly_revenue_trend.png'}")
print("Corrected monthly revenue used:")
print(series.to_string())
