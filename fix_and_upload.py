"""
fix_and_upload.py — Cleans dummy row, then uploads AR Aging.xlsx to Supabase.
Run this once to populate the database.
"""
from dotenv import load_dotenv
import os

load_dotenv()

from supabase import create_client
client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# ── Step 1: Delete the dummy row that was accidentally inserted ───────────────
print("Deleting dummy rows (where _row_hash is null)...")
client.table("ar_aging").delete().is_("_row_hash", "null").execute()
print("Done.")

# ── Step 2: Discover actual table columns from Supabase ──────────────────────
# Insert a blank row to get column names, then delete it
import httpx, json

resp = httpx.post(
    f"{os.environ['SUPABASE_URL']}/rest/v1/ar_aging",
    headers={
        "apikey": os.environ["SUPABASE_KEY"],
        "Authorization": f"Bearer {os.environ['SUPABASE_KEY']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    },
    content=b"{}",
)
if resp.status_code == 201:
    row = resp.json()[0]
    db_columns = set(row.keys()) - {"id"}
    # Delete that dummy row too
    dummy_id = row["id"]
    client.table("ar_aging").delete().eq("id", dummy_id).execute()
    print(f"DB columns ({len(db_columns)}):", sorted(db_columns))
else:
    print("Could not discover columns:", resp.text)
    exit(1)

# ── Step 3: Upload Excel, filtering to only DB columns ───────────────────────
from uploader import read_excel, hash_row
from datetime import datetime, timezone
import hashlib, json as _json

print("\nReading Excel...")
with open("AR Aging.xlsx", "rb") as f:
    df = read_excel(f)

print(f"Excel rows: {len(df)}, Excel cols: {len(df.columns)}")

# Filter df columns to only those that exist in DB
overlap = [c for c in df.columns if c in db_columns]
print(f"Matched cols: {len(overlap)}")
df_filtered = df[overlap].copy()

now = datetime.now(timezone.utc).isoformat()

# Fetch existing hashes
resp2 = client.table("ar_aging").select("_row_hash").execute()
existing_hashes = {r["_row_hash"] for r in (resp2.data or [])}

rows_to_upsert = []
unchanged = 0

for idx, row in df_filtered.iterrows():
    record = row.where(row.notna(), None).to_dict()
    row_hash = hash_row(record)
    record["_row_index"] = int(idx)
    record["_row_hash"] = row_hash
    record["_uploaded_at"] = now
    if row_hash in existing_hashes:
        unchanged += 1
    else:
        rows_to_upsert.append(record)

print(f"Rows to upload: {len(rows_to_upsert)}, unchanged: {unchanged}")

BATCH = 200
for i in range(0, len(rows_to_upsert), BATCH):
    batch = rows_to_upsert[i:i+BATCH]
    client.table("ar_aging").upsert(batch, on_conflict="_row_hash").execute()
    print(f"  Uploaded batch {i//BATCH + 1}/{(len(rows_to_upsert)-1)//BATCH + 1} ({len(batch)} rows)")

# Log the upload
client.table("upload_log").insert({
    "uploaded_at": now,
    "rows_added": len(rows_to_upsert),
    "rows_updated": 0,
    "rows_unchanged": unchanged,
    "filename": "AR Aging.xlsx",
}).execute()

print(f"\n✅ Upload complete: {len(rows_to_upsert)} rows added, {unchanged} unchanged.")
