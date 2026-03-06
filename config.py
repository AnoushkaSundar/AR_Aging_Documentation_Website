"""
config.py — Loads environment variables and initialises the Supabase client.
Import `supabase_client`, `TABLE_NAME`, and `LOG_TABLE` from here.
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
TABLE_NAME: str = os.environ.get("TABLE_NAME", "ar_aging")
LOG_TABLE: str = os.environ.get("LOG_TABLE", "upload_log")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError(
        "SUPABASE_URL and SUPABASE_KEY must be set in your .env file. "
        "Copy .env.example to .env and fill in your credentials."
    )

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
