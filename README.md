# Mamaearth Returns & Growth Intelligence Pipeline

**Capstone:** Data Analytics with AI & Gen AI · E&ICT Academy, IIT Roorkee  
**Pipeline:** SQLite SQL reporting → independent pandas cleaning/EDA → Gemini or deterministic offline SCR narrative.

## Business question
Are product returns concentrated in particular payment methods or customer segments, and how much can the team trust revenue trends when duplicate orders and unusually large quantities are present?

The pipeline keeps the three layers connected without allowing downstream steps to invent figures:

1. **SQL layer** stores the unchanged raw CSVs and runs relational reports on all 180 raw orders.
2. **Python layer** independently reads the original CSVs, standardizes values, removes natural-key duplicates, imputes missing fields, calculates order values, flags quantity outliers, prints the analysis, and writes computed findings to `narrator/findings.json`.
3. **Narrator layer** reads that generated JSON and produces a Situation–Complication–Resolution (SCR) report. If no API key exists—or Gemini fails—it uses a deterministic offline template. The numeric checker validates required figures and saves the actual narrative to `narrator/sample_output.txt`.

## Repository structure

```text
.
├── README.md
├── requirements.txt
├── .gitignore
├── sql/
│   ├── schema.sql
│   ├── seed_data.sql
│   └── reports.sql
├── data/
│   ├── customers.csv
│   ├── products.csv
│   └── orders.csv
├── analysis/
│   ├── clean_and_eda.py
│   └── visualize.py
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/
    ├── findings.json
    ├── generate_narrative.py
    └── sample_output.txt
```

`analysis/cleaned_orders.csv`, `analysis/merged_analysis.csv`, and `analysis/monthly_revenue.json` are generated intermediate artifacts used by the visualization step. They are reproducible and may be committed or ignored; this repository ignores them by default.

## Prerequisites

- Python 3.10+ (tested with Python 3.12-compatible code)
- SQLite 3
- Git
- Optional: a free Google AI Studio Gemini API key for the online narrator. The offline path requires no key and no network access.

## Run from a fresh clone — exact order

Run commands from the repository root.

### 0. Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you only want to run the SQL and offline Python pipeline, pandas and matplotlib are required; the Gemini package is only needed for the online path.

### 1. SQL relational layer

Create a fresh database and load the schema and seed rows:

```bash
sqlite3 mamaearth.db < sql/schema.sql
sqlite3 mamaearth.db < sql/seed_data.sql
sqlite3 mamaearth.db < sql/reports.sql
```

The schema enables foreign keys and defines `customers`, `products`, and `orders`. The seed script is generated from the committed CSVs and preserves blank discount/rating fields as SQL `NULL`. The seed script clears existing rows first, so re-running it reloads the source records. The `reports.sql` file contains all requested reports and comments documenting expected outputs.

Expected initial counts: customers **45**, products **16**, orders **180**. Report (a) should show raw revenue **₹99,860.20** and average order value **₹554.78**. Report (b) should show **180** rows, **165** rated rows, and **15** unrated rows.

**Important:** `reports.sql` includes an `ALTER TABLE` for Task (i), so run it once per fresh database. If you want to rerun the reports after Task (i), recreate the database using the commands above first, otherwise SQLite will correctly report that `loyalty_tier` already exists.

You can also inspect counts individually:

```bash
sqlite3 mamaearth.db "SELECT COUNT(*) FROM customers;"
sqlite3 mamaearth.db "SELECT COUNT(*) FROM products;"
sqlite3 mamaearth.db "SELECT COUNT(*) FROM orders;"
```

### 2. Python cleaning, EDA, and visualizations

The Python layer deliberately reads the raw CSVs directly rather than querying SQLite. Run the cleaning/analysis script first:

```bash
python analysis/clean_and_eda.py
```

It prints each intermediate acceptance result, normalizes payment methods, detects and removes five duplicate rows using the natural key (not `order_id`), imputes missing discounts/ratings, reconciles raw vs cleaned revenue, flags quantity outliers without deleting them, evaluates payment and city-tier return rates, labels all six correlations, and compares monthly revenue with and without the flagged outliers. It then writes generated intermediates and **writes `narrator/findings.json` from the computed values**.

Next, create the PNGs:

```bash
python analysis/visualize.py
```

This generates `visualizations/return_rate_by_payment.png` and `visualizations/monthly_revenue_trend.png`. The monthly chart uses the outlier-corrected series, not the inflated one.

Expected core results include:

- 5 duplicate rows removed: `O0176`–`O0180`; 175 cleaned rows remain.
- Cleaned revenue: **₹97,358.30**; raw revenue: **₹99,860.20**; duplicate-driven delta: **₹2,501.90**.
- COD return rate: **44.4%**; CARD: **14.7%**; UPI: **18.9%**.
- Highest-risk segment: COD + Tier-2 cities at **54.5%**.
- Outlier-corrected peak: **March 2026**, revenue **₹20,318.90**.

### 3. GenAI narrator — Gemini or offline

No key is needed for the default offline run:

```bash
python narrator/generate_narrative.py
```

The script reads `narrator/findings.json`, generates the SCR report, runs a numeric accuracy checker, and writes the actual narrative to `narrator/sample_output.txt`. If there is no key, the deterministic offline template runs with no network call.

To use Gemini, create a free API key in Google AI Studio and set it in your shell (never commit the key):

```bash
export GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
python narrator/generate_narrative.py
```

`GEMINI_API_KEY` is also accepted. You can optionally set `GEMINI_MODEL` to a model available to your account; the default is `gemini-2.5-flash`. The call uses temperature `0.0`, an explicit output-token limit, a 30-second client timeout, and error handling. If the API call fails, the offline template is used and the script reports the mode. The saved sample is checked at grading time; no live API call is required to grade the repository.

## Data quality and business interpretation

- The source CSV files are committed unchanged. All cleaning occurs in Python.
- Blank discount values are treated as 0% for revenue, while missing ratings are imputed with the median after deduplication.
- Duplicate detection excludes `order_id` from the natural key because the duplicated records have different IDs by design.
- Quantity outliers are flagged for the time-series comparison rather than deleted from the cleaned dataset.
- The COD return-rate association is a signal for operational investigation, not proof that payment method causes returns.
- The revenue measure is order value after listed discount; it is not profit or margin because cost-of-goods, shipping, and reverse-logistics costs are not provided.

## GitHub publishing steps

1. Create a new **public** repository on GitHub, for example `mamaearth-returns-growth-intelligence`. Do not initialize it with a README if you already have this local project.
2. From this project directory, initialize Git and commit the files:

   ```bash
   git init
   git add README.md requirements.txt .gitignore sql data analysis visualizations narrator
   git status
   git commit -m "Build Mamaearth returns and growth intelligence pipeline"
   ```

3. Add your new repository URL and push the default branch (replace the URL with your own):

   ```bash
   git branch -M main
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/mamaearth-returns-growth-intelligence.git
   git push -u origin main
   ```

4. Open the repository page in a browser and verify that it is public, the README renders, the three original CSVs are present, both PNGs are visible, and `narrator/findings.json` plus `narrator/sample_output.txt` are committed.
5. Copy the public repository URL as the capstone submission link. Never commit `.venv/`, database files, API keys, or other secrets.

## Reproducibility checklist

```bash
# SQL layer (fresh database)
rm -f mamaearth.db
sqlite3 mamaearth.db < sql/schema.sql
sqlite3 mamaearth.db < sql/seed_data.sql
sqlite3 mamaearth.db < sql/reports.sql

# Analysis and visuals
python analysis/clean_and_eda.py
python analysis/visualize.py

# Narrator with no key (offline fallback)
unset GOOGLE_API_KEY GEMINI_API_KEY
python narrator/generate_narrative.py

git status --short
```
