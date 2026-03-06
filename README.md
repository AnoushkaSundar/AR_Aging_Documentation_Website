# AR Aging Dashboard — Setup Guide

## What This Is
An interactive Streamlit dashboard that:
- Reads `AR Aging.xlsx` (with headers on row 6)
- Uploads data to Supabase with **change detection** (only new/changed rows are re-sent)
- Provides filters by **Customer Name, Customer ID, Profit Center, Segment, Region** + any other column
- Shows **KPI cards, 7 charts, full data table, CSV export, and upload log**

---

## One-Time Setup

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Create Supabase tables
1. Go to [supabase.com](https://supabase.com) → your project → **SQL Editor**
2. Open `schema.sql` from this folder
3. Paste all contents into the editor and click **Run**

### Step 3 — Configure credentials
```bash
# Copy the template
copy .env.example .env
```
Then open `.env` and fill in:
```
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGci...  (your anon/public key)
TABLE_NAME=ar_aging
LOG_TABLE=upload_log
```
Find your URL and key at: **Supabase → Settings → API**

### Step 4 — Launch
```bash
# Option A: double-click
run.bat

# Option B: terminal
streamlit run app.py
```

---

## Daily Usage

1. Open the dashboard (http://localhost:8501)
2. Drag your updated `AR Aging.xlsx` onto the **Upload** area in the sidebar
3. Click **⬆️ Upload to Supabase**
4. Only changed rows are sent — fast & efficient
5. Use sidebar filters to drill down
6. Export filtered data via **⬇️ Download as CSV**

---

## Dashboard Features

| Tab | Contents |
|---|---|
| **📊 Overview** | 8 KPI cards + aging bucket bar chart |
| **📈 Charts** | Region bar, Segment pie, Top customers, Profit Center bar, Stacked aging, Overdue scatter, Heatmap |
| **📋 Data Table** | Column picker, full-text search, CSV download, pivot summary |
| **📁 Upload Log** | History of all upload sessions |

---

## Adding More Filters

The sidebar has an **"➕ Add more filter categories"** expander. It automatically lists all categorical columns. Just expand it and select from any column — the entire dashboard updates instantly.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `EnvironmentError` on startup | `.env` file is missing or has wrong credentials |
| `Upload failed` | Check that you ran `schema.sql` first; also verify your Supabase key has `INSERT` permission |
| Charts show empty | Upload data first, then reload the page |
| Wrong column mapping | The Excel file must have headers on **row 6** (standard Sandvik AR Aging format) |
