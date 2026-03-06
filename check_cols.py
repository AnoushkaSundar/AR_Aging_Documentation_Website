"""check_cols.py — Discover what columns exist in Supabase ar_aging table"""
from dotenv import load_dotenv
import os, httpx, json

load_dotenv()

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_KEY']

resp = httpx.get(
    f"{url}/rest/v1/",
    headers={"apikey": key, "Authorization": f"Bearer {key}"},
)
schema = resp.json()

if "definitions" in schema:
    cols = list(schema["definitions"].get("ar_aging", {}).get("properties", {}).keys())
    print("Columns from schema definitions:", cols)
else:
    # Try newer format using OpenAPI paths
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        if "ar_aging" in path:
            params = methods.get("get", {}).get("parameters", [])
            for p in params:
                if p.get("name") == "select":
                    pass
    # Fall back to introspect via column endpoint
    col_resp = httpx.get(
        f"{url}/rest/v1/ar_aging?select=*&limit=0",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Range": "0-0"},
    )
    print("Status:", col_resp.status_code)
    print("Headers:", dict(col_resp.headers))
    # Try to get column names via a blank insert error
    ins = httpx.post(
        f"{url}/rest/v1/ar_aging",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json", "Prefer": "return=representation"},
        content=b"{}",
    )
    print("Insert response:", ins.status_code, ins.text[:500])
