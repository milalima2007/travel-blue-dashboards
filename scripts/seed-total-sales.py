#!/usr/bin/env python3
"""
seed-total-sales.py
-------------------
Reads total-sales-bp-latam/data/sales_data.json and config.json
and inserts (or updates) them into the Supabase project_data table
as composite_key = 'sales_data' and composite_key = 'config'.

Usage:
  pip install supabase python-dotenv
  python scripts/seed-total-sales.py

Environment variables (set in .env or export them):
  SUPABASE_URL          — your project URL  (e.g. https://xxxxx.supabase.co)
  SUPABASE_SERVICE_KEY  — service_role key  (NOT the anon key)
"""

import json
import os
import sys
from pathlib import Path

# ── Load env ──────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional; env vars can be exported directly

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
    print("  export SUPABASE_URL=https://xxxxx.supabase.co")
    print("  export SUPABASE_SERVICE_KEY=eyJ...")
    sys.exit(1)

# ── Locate JSON files ──────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_DIR    = REPO_ROOT / "total-sales-bp-latam" / "data"
SALES_FILE  = DATA_DIR / "sales_data.json"
CONFIG_FILE = DATA_DIR / "config.json"

for f in (SALES_FILE, CONFIG_FILE):
    if not f.exists():
        print(f"ERROR: file not found: {f}")
        sys.exit(1)

sales_data = json.loads(SALES_FILE.read_text(encoding="utf-8"))
config     = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

# ── Upsert into project_data ───────────────────────────────────────────────
try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase package not installed. Run:  pip install supabase")
    sys.exit(1)

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

PROJECT_SLUG = "total-sales-bp-latam"

rows = [
    {"project_slug": PROJECT_SLUG, "composite_key": "sales_data", "row_data": sales_data},
    {"project_slug": PROJECT_SLUG, "composite_key": "config",     "row_data": config},
]

response = (
    client.table("project_data")
    .upsert(rows, on_conflict="project_slug,composite_key")
    .execute()
)

if hasattr(response, "error") and response.error:
    print(f"ERROR from Supabase: {response.error}")
    sys.exit(1)

print(f"Done. Upserted {len(rows)} rows into project_data for slug '{PROJECT_SLUG}'.")
print("  composite_key='sales_data'  →  full sales_data.json object")
print("  composite_key='config'      →  full config.json object")
