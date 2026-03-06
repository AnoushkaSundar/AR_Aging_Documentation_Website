"""
uploader.py — Reads AR Aging Excel, detects changed rows via SHA-256, upserts to Supabase.
"""
import hashlib
import json
from datetime import datetime, timezone

import pandas as pd


# ── Column name cleaning ──────────────────────────────────────────────────────
def clean_col(name: str) -> str:
    """Normalise a column name to snake_case for Supabase."""
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("&", "and")
        .replace(".", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("%", "pct")
    )


# ── Excel reader ──────────────────────────────────────────────────────────────
def read_excel(file_obj) -> pd.DataFrame:
    """
    Read the AR Aging Excel file.
    Headers are on row 6 (0-indexed: 5).
    Returns a cleaned DataFrame.
    """
    df = pd.read_excel(file_obj, header=5, engine="openpyxl")

    # Drop entirely empty rows and columns
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)

    # Clean column names
    df.columns = [clean_col(c) for c in df.columns]

    # Deduplicate column names (e.g. segment vs segment_1)
    seen: dict = {}
    new_cols = []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols

    # Convert date columns
    for col in df.columns:
        if "date" in col or col in ("pduedate",):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            except Exception:
                pass

    # Coerce numeric columns that should be numbers
    numeric_hints = ["outstanding_value", "original_amount", "goods_amount", "vat_amount",
                     "overdue_days", "credit_limit", "availablecreditlimit", "sumifs"]
    for col in numeric_hints:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ── Row hashing ───────────────────────────────────────────────────────────────
def hash_row(row: dict) -> str:
    """Stable SHA-256 of a row dict (excluding meta columns)."""
    stable = {k: str(v) for k, v in sorted(row.items()) if not k.startswith("_")}
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()


# ── Discover DB columns ────────────────────────────────────────────────────────
def get_db_columns(supabase_client, table: str) -> set:
    """
    Returns the set of column names that actually exist in the Supabase table,
    by inserting an empty row and reading back the column names, then deleting it.
    Excludes 'id' (auto-generated).
    """
    try:
        import httpx, os
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        resp = httpx.post(
            f"{url}/rest/v1/{table}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            content=b"{}",
            timeout=15,
        )
        if resp.status_code == 201:
            row = resp.json()[0]
            dummy_id = row["id"]
            supabase_client.table(table).delete().eq("id", dummy_id).execute()
            return set(row.keys()) - {"id"}
    except Exception:
        pass
    return set()


# ── Main upload function ───────────────────────────────────────────────────────
def upload_excel(file_obj, supabase_client, table: str, log_table: str, filename: str) -> dict:
    """
    Full pipeline: read → discover DB cols → filter → hash (with filename) → upsert → log.
    Rows from different files are always kept separate via the source_file field.
    Returns {added, updated, unchanged, total}.
    """
    df = read_excel(file_obj)
    now = datetime.now(timezone.utc).isoformat()

    # Discover which columns the DB table actually has
    db_cols = get_db_columns(supabase_client, table)
    if db_cols:
        meta_cols = {"_row_hash", "_row_index", "_uploaded_at", "source_file"}
        valid_df_cols = [c for c in df.columns if c in (db_cols - meta_cols)]
        df = df[valid_df_cols].copy()

    # Fetch existing hashes for THIS source file only
    resp = supabase_client.table(table).select("_row_hash").execute()
    existing_hashes = {r["_row_hash"] for r in (resp.data or [])}

    rows_to_upsert = []
    unchanged = 0

    for idx, row in df.iterrows():
        record = row.where(row.notna(), None).to_dict()
        # Include filename in hash so identical rows from different files are distinct
        record["source_file"] = filename
        row_hash = hash_row(record)
        record["_row_index"] = int(idx)
        record["_row_hash"] = row_hash
        record["_uploaded_at"] = now

        if row_hash in existing_hashes:
            unchanged += 1
        else:
            rows_to_upsert.append(record)

    # Upsert in batches of 200
    BATCH = 200
    for i in range(0, len(rows_to_upsert), BATCH):
        batch = rows_to_upsert[i : i + BATCH]
        supabase_client.table(table).upsert(batch, on_conflict="_row_hash").execute()

    added = len(rows_to_upsert)

    # Log the upload session
    supabase_client.table(log_table).insert({
        "uploaded_at": now,
        "rows_added": added,
        "rows_updated": 0,
        "rows_unchanged": unchanged,
        "filename": filename,
    }).execute()

    return {"added": added, "updated": 0, "unchanged": unchanged, "total": len(df)}

