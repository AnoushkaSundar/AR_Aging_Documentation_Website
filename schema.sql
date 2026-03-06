-- Run this ONCE in your Supabase SQL Editor before using the dashboard.
-- Go to: https://supabase.com → Your Project → SQL Editor → New Query → Paste → Run

-- ─────────────── Main AR Aging table ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ar_aging (
  id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  _row_index            INTEGER,
  _row_hash             TEXT UNIQUE,
  _uploaded_at          TIMESTAMPTZ DEFAULT NOW(),

  -- Core identification
  entity                TEXT,
  gl_account            TEXT,
  segment               TEXT,
  globalcustomer        TEXT,
  origacct              TEXT,
  customer_name         TEXT,
  customer_number       TEXT,
  profit_center         TEXT,
  region                TEXT,
  pa_division           TEXT,
  dealer                TEXT,
  customer_type         TEXT,
  classification        TEXT,
  pc                    TEXT,
  comb                  TEXT,
  source_file           TEXT,    -- tracks which Excel file this row came from

  -- Financial amounts
  outstanding_value     NUMERIC,
  original_amount       NUMERIC,
  goods_amount          NUMERIC,
  vat_amount            NUMERIC,
  credit_limit          NUMERIC,
  availablecreditlimit  NUMERIC,
  sumifs                NUMERIC,

  -- Dates
  document_date         DATE,
  pduedate              DATE,

  -- Payment info
  overdue_days          NUMERIC,
  bucket                TEXT,
  payment_terms         TEXT,
  ccy                   TEXT,

  -- References
  document_ref          TEXT,
  po_ref                TEXT,
  order_nr              TEXT,
  job_category          TEXT,
  group_code            TEXT,
  pa_and_doc_ref_no     TEXT,
  external_text         TEXT,
  nota_fiscal_number    TEXT,
  product_account       TEXT,
  salesman_name         TEXT,
  salesman              TEXT,
  dseq                  TEXT,
  remark                TEXT,
  type                  TEXT,
  dr_cr                 TEXT,
  segment_1             TEXT,
  entity2               TEXT,
  customer_class        NUMERIC
);

-- Index for fast filtering on key columns
CREATE INDEX IF NOT EXISTS idx_ar_region ON ar_aging(region);
CREATE INDEX IF NOT EXISTS idx_ar_segment ON ar_aging(segment);
CREATE INDEX IF NOT EXISTS idx_ar_profit_center ON ar_aging(profit_center);
CREATE INDEX IF NOT EXISTS idx_ar_customer_name ON ar_aging(customer_name);
CREATE INDEX IF NOT EXISTS idx_ar_bucket ON ar_aging(bucket);

-- ─────────────── Upload log table ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS upload_log (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  uploaded_at   TIMESTAMPTZ DEFAULT NOW(),
  rows_added    INTEGER,
  rows_updated  INTEGER,
  rows_unchanged INTEGER,
  filename      TEXT
);
