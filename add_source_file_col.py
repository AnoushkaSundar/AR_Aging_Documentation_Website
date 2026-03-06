"""
add_source_file_col.py
Adds source_file column to ar_aging table and tags existing rows as 'AR Aging.xlsx'.
Run once.
"""
from dotenv import load_dotenv
import os, httpx

load_dotenv()

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_KEY"]

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
}

# Use Supabase SQL endpoint (requires service_role key, so we use REST PATCH as fallback)
# Instead: update all rows via REST to add the source_file value
from supabase import create_client
client = create_client(url, key)

# Patch all existing rows that have no source_file yet
print("Tagging existing rows with source_file = 'AR Aging.xlsx' ...")

# Fetch all ids
resp = client.table("ar_aging").select("id, source_file").execute()
rows = resp.data or []
to_update = [r["id"] for r in rows if not r.get("source_file")]
print(f"Rows to tag: {len(to_update)}")

BATCH = 200
for i in range(0, len(to_update), BATCH):
    batch_ids = to_update[i:i+BATCH]
    for rid in batch_ids:
        client.table("ar_aging").update({"source_file": "AR Aging.xlsx"}).eq("id", rid).execute()
    print(f"  Tagged {min(i+BATCH, len(to_update))}/{len(to_update)}")

print("Done. All existing rows tagged as 'AR Aging.xlsx'.")
