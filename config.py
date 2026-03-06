"""
config.py — Loads Supabase credentials.

Priority:
  1. Streamlit Cloud secrets (st.secrets) — used when deployed on share.streamlit.io
  2. Local .env file — used when running locally

This means the same code works both locally and in the cloud without any changes.
"""
import os
from dotenv import load_dotenv

# Load .env for local development (no-op if file doesn't exist)
load_dotenv()


def _get(key: str, default: str = "") -> str:
    """Try st.secrets first, then env vars, then default."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)


SUPABASE_URL: str = _get("SUPABASE_URL")
SUPABASE_KEY: str = _get("SUPABASE_KEY")
TABLE_NAME: str   = _get("TABLE_NAME", "ar_aging")
LOG_TABLE: str    = _get("LOG_TABLE", "upload_log")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError(
        "SUPABASE_URL and SUPABASE_KEY are not set.\n"
        "  • Local: copy .env.example → .env and fill in your credentials.\n"
        "  • Cloud: add them in the Streamlit Cloud dashboard under App Settings → Secrets."
    )

from supabase import create_client, Client
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
