#!/usr/bin/env python3
"""
update_monthly_data.py — Monthly Sales Data Importer
=====================================================
Reads country-specific monthly Excel files, normalises their structure
to match the main database, fills missing classification columns from the
existing reference data, and appends the new records.  Then regenerates
both dashboards automatically.

Usage
-----
  python update_monthly_data.py                       # auto-detect files in the same folder
  python update_monthly_data.py <folder>              # look for files in <folder>
  python update_monthly_data.py <file1> [<file2>...]  # process specific files
  python update_monthly_data.py --dry-run             # preview without writing

Country is detected automatically from the filename.
Every run is idempotent: existing REAL rows for the same
YEAR + MONTH + COUNTRY are removed before the new rows are inserted.
A timestamped backup is created before any write.
"""

import sys
import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output on Windows (avoids cp1252 encode errors for box-drawing chars)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
EXCEL           = BASE_DIR / "ANALISE Q1 2026 2.xlsx"
SHEET           = "SALES_SYSTEM_DATABASE"
BACKUP_DIR      = BASE_DIR / "backups"
GENERATOR_LATAM = BASE_DIR / "generate_latam_q1_2026.py"
GENERATOR_CTRY  = BASE_DIR / "generate_country_q1_2026.py"

# Exact column order in the main DB (including the trailing space in 'SKU ')
DB_COLUMNS = [
    'DATE', 'YEAR', 'MONTH', 'CUSTOMER', 'CHANNEL', 'NF',
    'SKU SYSTEM', 'SKU ', 'SKU 2', 'BRAND', 'DESCRIPTION',
    'FAMILY', 'CATEGORY', 'SUB-CATEGORY', 'EXCHANGE RATE',
    'NET AMOUNT (LcCy)', 'NET AMOUNT (USD)', 'QTY',
    'COUNTRY', 'BRAND 2', 'TYPE', 'FAMILY 2', 'CUSTOMER 3', 'BRAND 3', 'OBS',
]

# Portuguese month abbreviations
MONTH_PT = {
    1: 'jan', 2: 'fev',  3: 'mar', 4: 'abr',
    5: 'mai', 6: 'jun',  7: 'jul', 8: 'ago',
    9: 'set', 10: 'out', 11: 'nov', 12: 'dez',
}

# ──────────────────────────────────────────────────────────────────────────────
# Per-country file configuration
# ──────────────────────────────────────────────────────────────────────────────
# file_kw   : keyword(s) in the filename used to identify the country
# header    : row index to use as header when reading the DATABASE sheet
# filter_col: column whose value must NOT equal filter_val to keep the row
# filter_val: value to reject (case-insensitive)
# col_map   : rename rules  { source_col : target_col }
#             'SKU' always maps to 'SKU ' (with trailing space, matching the DB)
# nf_col    : source column name for the NF/invoice number field
COUNTRY_CONFIGS = {
    'BRAZIL': {
        'file_kw':    ['brazil', 'brasil'],
        'header':     0,
        'filter_col': None,
        'col_map': {
            'SKU':          'SKU ',
            'SKU2':         'SKU 2',
            'BRAND2':       'BRAND 2',
            'QUANTITY':     'QTY',
            'Nota Fiscal':  'NF',
        },
    },
    'MEXICO': {
        'file_kw':    ['mex'],
        'header':     1,
        'filter_col': None,   # Include ALL rows (CANCELADO = credit notes, negative amounts)
        'col_map': {
            'SKU':      'SKU ',
            'QUANTITY': 'QTY',
            # SKU 2, BRAND 2, NF already correct in Mexico file
        },
    },
    'COLOMBIA': {
        'file_kw':    ['col'],
        'header':     0,
        'filter_col': None,
        'col_map': {
            'SKU':      'SKU ',
            'SKU2':     'SKU 2',
            'BRAND2':   'BRAND 2',
            'QUANTITY': 'QTY',
            # NF: handled dynamically (encoding issues with 'Número comprobante')
        },
        'nf_search':  'comprobante',   # fallback: find col containing this string
    },
    'PANAMA': {
        'file_kw':    ['pan'],
        'header':     0,
        'filter_col': None,
        'col_map': {
            'SKU':      'SKU ',
            'QUANTITY': 'QTY',
        },
        # CATEGORY, SUB-CATEGORY, BRAND 2 are absent → filled from SKU reference
    },
    'ARGENTINA': {
        'file_kw':    ['arg'],
        'header':     0,
        'filter_col': None,
        'col_map': {
            'SKU':               'SKU ',
            'SKU 2':             'SKU 2',
            'BRAND2':            'BRAND 2',
            'QUANTITY':          'QTY',
            'Nro. Comprobante':  'NF',
        },
    },
    'CHILE': {
        'file_kw':    ['chile', 'chi'],
        'header':     0,
        'filter_col': None,
        'col_map': {
            'SKU':                  'SKU ',
            'BRAND2':               'BRAND 2',
            'QUANTITY':             'QTY',
            'Numero del documento': 'NF',
        },
    },
    'PERU': {
        'file_kw':    ['per'],
        'header':     0,
        'filter_col': None,
        'col_map': {
            'SKU':      'SKU ',
            'BRAND2':   'BRAND 2',
            'QUANTITY': 'QTY',
        },
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def detect_country(filepath: Path) -> str | None:
    """Return the COUNTRY name based on keywords in the filename."""
    name_lower = filepath.stem.lower()
    for country, cfg in COUNTRY_CONFIGS.items():
        if any(kw in name_lower for kw in cfg['file_kw']):
            return country
    return None


def backup_excel():
    BACKUP_DIR.mkdir(exist_ok=True)
    ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = BACKUP_DIR / f"ANALISE_Q1_2026_backup_{ts}.xlsx"
    shutil.copy2(EXCEL, dest)
    print(f"  ✔ Backup → {dest.name}")


def load_main_db() -> pd.DataFrame:
    print(f"\nLoading main database ({EXCEL.name}) …")
    df = pd.read_excel(EXCEL, sheet_name=SHEET)
    print(f"  {len(df):,} rows")
    return df


def save_main_db(df: pd.DataFrame):
    backup_excel()
    print(f"\nSaving {len(df):,} rows to {EXCEL.name} …")
    df.to_excel(EXCEL, sheet_name=SHEET, index=False)
    print("  ✔ Saved.")


def build_sku_ref(db: pd.DataFrame) -> pd.DataFrame:
    """
    Build a SKU-level reference table from existing REAL rows.
    Columns: SKU 2, BRAND, BRAND 2, BRAND 3, FAMILY, FAMILY 2,
             CATEGORY, SUB-CATEGORY, DESCRIPTION
    """
    real = db[db['TYPE'] == 'REAL'].copy()
    # Normalise SKU 2 to string BEFORE grouping to avoid mixed int/str duplicates
    real['SKU 2'] = real['SKU 2'].astype(str).str.strip()
    ref_cols = ['SKU 2', 'BRAND', 'BRAND 2', 'BRAND 3',
                'FAMILY', 'FAMILY 2', 'CATEGORY', 'SUB-CATEGORY', 'DESCRIPTION']
    ref = (real.dropna(subset=['SKU 2'])
               .groupby('SKU 2', as_index=False)
               .first()[ref_cols])
    # Drop any remaining duplicates (keep first occurrence)
    ref = ref.drop_duplicates(subset='SKU 2', keep='first')
    return ref.set_index('SKU 2')


def build_customer_ref(db: pd.DataFrame) -> pd.Series:
    """
    Build a (CUSTOMER, COUNTRY) → CUSTOMER 3 mapping.
    When a customer has multiple values the most recent non-OTHERS one wins.
    """
    real = db[db['TYPE'] == 'REAL'].copy()
    # prefer non-OTHERS values; fallback to the most common one
    cref = {}
    for (cust, ctry), grp in real.groupby(['CUSTOMER', 'COUNTRY']):
        vals = grp['CUSTOMER 3'].dropna()
        non_others = vals[vals != 'OTHERS']
        if len(non_others):
            cref[(cust, ctry)] = non_others.iloc[-1]
        elif len(vals):
            cref[(cust, ctry)] = vals.iloc[-1]
    return cref


def find_nf_col(df: pd.DataFrame, cfg: dict, country: str) -> str | None:
    """Locate the invoice-number column, handling encoding noise."""
    # Explicit mapping from col_map?
    if 'NF' in df.columns:
        return None  # already named correctly
    # Search by substring
    search_kw = cfg.get('nf_search', '')
    if search_kw:
        for col in df.columns:
            if search_kw.lower() in str(col).lower():
                return col
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Core normaliser
# ──────────────────────────────────────────────────────────────────────────────
def normalise_country_file(
    filepath: Path,
    country: str,
    sku_ref: pd.DataFrame,
    cust_ref: dict,
) -> pd.DataFrame:
    """
    Read one country monthly file and return a DataFrame aligned
    to DB_COLUMNS, ready to append to the main database.
    """
    cfg = COUNTRY_CONFIGS[country]
    print(f"\n  [{country}] Reading {filepath.name} …")

    # Auto-detect sheet name: prefer 'DATABASE', else first sheet containing
    # 'DATA', 'SALES', or 'BASE' in its name, else the first sheet.
    xl = pd.ExcelFile(filepath)
    sheet = None
    for s in xl.sheet_names:
        if s.strip().upper() == 'DATABASE':
            sheet = s
            break
    if sheet is None:
        for s in xl.sheet_names:
            su = s.strip().upper()
            if any(kw in su for kw in ('DATA', 'SALES', 'BASE', 'VENDA', 'VENTA')):
                sheet = s
                break
    if sheet is None:
        sheet = xl.sheet_names[0]
    print(f"    Using sheet: '{sheet}'")

    df = pd.read_excel(filepath, sheet_name=sheet, header=cfg['header'])
    print(f"    {len(df):,} raw rows, {len(df.columns)} columns")

    # ── 1. Strip whitespace from column names ──────────────────────────────
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]

    # ── 2. Find & rename NF column if needed ──────────────────────────────
    nf_src = find_nf_col(df, cfg, country)
    if nf_src and nf_src in df.columns:
        df = df.rename(columns={nf_src: 'NF'})

    # ── 3. Apply column renaming map ───────────────────────────────────────
    df = df.rename(columns=cfg['col_map'])

    # ── 4. Filter bad rows (e.g. CANCELADO in Mexico) ──────────────────────
    if cfg.get('filter_col') and cfg['filter_col'] in df.columns:
        bad_val  = cfg.get('filter_val', '').upper()
        mask_bad = df[cfg['filter_col']].astype(str).str.upper() == bad_val
        n_removed = mask_bad.sum()
        df = df[~mask_bad].reset_index(drop=True)
        if n_removed:
            print(f"    Removed {n_removed} '{cfg['filter_val']}' rows")

    # ── 5. Drop completely empty rows ──────────────────────────────────────
    df = df.dropna(how='all').reset_index(drop=True)

    # ── 5b. Auto-detect DATE column if not named 'DATE' ───────────────────
    if 'DATE' not in df.columns:
        # Look for any column whose name contains 'date', 'fecha', 'data'
        date_col = None
        for col in df.columns:
            if any(kw in str(col).lower() for kw in ('date', 'fecha', 'data')):
                date_col = col
                break
        if date_col:
            print(f"    DATE column not found — using '{date_col}' instead")
            df = df.rename(columns={date_col: 'DATE'})
        else:
            print(f"    WARNING: No DATE column found. Columns available:")
            print(f"    {list(df.columns)}")
            raise ValueError(f"No DATE column found in {filepath.name}. "
                             f"Available columns: {list(df.columns)}")

    # ── 6. Coerce / derive core fields ────────────────────────────────────
    # Some files store dates as Excel serial numbers (integers) — convert those first
    EXCEL_EPOCH = pd.Timestamp('1899-12-30')
    if df['DATE'].dtype == object or str(df['DATE'].dtype).startswith('int'):
        def _parse_date(v):
            if pd.isna(v):
                return pd.NaT
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                # Excel serial number → date
                try:
                    return EXCEL_EPOCH + pd.Timedelta(days=int(v))
                except Exception:
                    return pd.NaT
            return v
        df['DATE'] = df['DATE'].apply(_parse_date)
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce', dayfirst=True)
    df = df.dropna(subset=['DATE']).reset_index(drop=True)
    df['YEAR']  = df['DATE'].dt.year
    df['MONTH'] = df['DATE'].dt.month.map(MONTH_PT)
    df['COUNTRY'] = country
    df['TYPE']    = 'REAL'

    # ── 7. Normalise SKU 2 to string ───────────────────────────────────────
    if 'SKU 2' in df.columns:
        df['SKU 2'] = df['SKU 2'].astype(str).str.strip()

    # ── 8. Fill reference columns from SKU lookup ──────────────────────────
    fill_from_sku = ['BRAND', 'BRAND 2', 'BRAND 3', 'FAMILY', 'FAMILY 2',
                     'CATEGORY', 'SUB-CATEGORY', 'DESCRIPTION']

    for col in fill_from_sku:
        if col not in df.columns:
            df[col] = None  # create missing column

    if 'SKU 2' in df.columns and len(sku_ref):
        for col in fill_from_sku:
            if col not in sku_ref.columns:
                continue
            # Only fill rows where value is missing or blank
            needs_fill = (
                df[col].isna() |
                df[col].astype(str).str.strip().isin(['', 'nan', 'None'])
            )
            if needs_fill.any():
                mapped = df.loc[needs_fill, 'SKU 2'].map(sku_ref[col])
                df.loc[needs_fill, col] = mapped

    # Apply default 'OTHERS' for anything still missing
    for col in ['BRAND 2', 'BRAND 3', 'FAMILY 2', 'CATEGORY', 'SUB-CATEGORY']:
        df[col] = df[col].fillna('OTHERS')
        df.loc[df[col].astype(str).str.strip().isin(['', 'nan', 'None']), col] = 'OTHERS'

    # ── 9. Fill CUSTOMER 3 from customer reference ─────────────────────────
    if 'CUSTOMER 3' not in df.columns:
        df['CUSTOMER 3'] = None

    needs_c3 = (
        df['CUSTOMER 3'].isna() |
        df['CUSTOMER 3'].astype(str).str.strip().isin(['', 'nan', 'None'])
    )
    if needs_c3.any():
        df.loc[needs_c3, 'CUSTOMER 3'] = df[needs_c3].apply(
            lambda r: cust_ref.get((r['CUSTOMER'], country), 'OTHERS'), axis=1
        )

    # ── 10. Ensure all DB columns exist (fill with None if absent) ─────────
    for col in DB_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # ── 10b. Apply FAMILY 2 classification rules ───────────────────────────
    for c in ['BRAND 2', 'FAMILY', 'FAMILY 2', 'CATEGORY']:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    tb  = df['BRAND 2'] == 'TRAVEL BLUE'
    ntb = ~tb

    # Non-TB brands: FAMILY 2 = brand name
    df.loc[ntb, 'FAMILY 2'] = df.loc[ntb, 'BRAND 2']

    # TB brand: FAMILY 2 = FAMILY value
    df.loc[tb, 'FAMILY 2'] = df.loc[tb, 'FAMILY']

    # TB TECH or MEMORY → TRAVEL ACCESSORIES
    tech_mem = tb & (
        (df['FAMILY'] == 'TECH') |
        (df['FAMILY'].str.upper().str.contains('MEMORY', na=False))
    )
    df.loc[tech_mem, 'FAMILY 2'] = 'TRAVEL ACCESSORIES'

    # CATEGORY = SECURITY → FAMILY 2 = SECURITY (all brands)
    sec = df['CATEGORY'] == 'SECURITY'
    df.loc[sec, 'FAMILY 2'] = 'SECURITY'

    print(f"    FAMILY 2 rules: TB={tb.sum()} non-TB={ntb.sum()} TECH/MEM→TA={tech_mem.sum()} SEC={sec.sum()}")

    # ── 11. Select & reorder to match DB_COLUMNS exactly ──────────────────
    result = df[DB_COLUMNS].copy()

    period_summary = result.groupby(['YEAR', 'MONTH']).size()
    print(f"    Normalised: {len(result):,} rows")
    for (yr, mo), n in period_summary.items():
        print(f"      {yr} {mo}: {n:,} rows")

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard regeneration
# ──────────────────────────────────────────────────────────────────────────────
def regenerate_dashboards():
    for label, script in [('LATAM', GENERATOR_LATAM), ('Country', GENERATOR_CTRY)]:
        print(f"\n  Regenerating {label} dashboard …")
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"    ✔ {label} dashboard OK")
            for line in result.stdout.strip().split('\n')[-3:]:
                if line.strip():
                    print(f"      {line.strip()}")
        else:
            print(f"    ✘ ERROR in {label} dashboard:")
            print(result.stderr[-2000:])


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def run(source_files: list[Path], dry_run: bool = False):
    if not source_files:
        print("No source files found / provided.")
        return

    # Load main DB once
    db = load_main_db()

    # Build reference tables
    print("\nBuilding reference tables …")
    sku_ref  = build_sku_ref(db)
    cust_ref = build_customer_ref(db)
    print(f"  SKU reference: {len(sku_ref):,} unique SKUs")
    print(f"  Customer reference: {len(cust_ref):,} unique (customer, country) pairs")

    # Normalise each source file
    new_frames = []
    unrecognised = []

    for fp in source_files:
        country = detect_country(fp)
        if not country:
            unrecognised.append(fp)
            print(f"\n  ⚠  Could not detect country for: {fp.name} — skipped")
            continue
        try:
            normalised = normalise_country_file(fp, country, sku_ref, cust_ref)
            new_frames.append(normalised)
        except Exception as exc:
            print(f"\n  ✘ Error processing {fp.name}: {exc}")
            raise

    if not new_frames:
        print("\nNo valid data to import.")
        return

    all_new = pd.concat(new_frames, ignore_index=True)
    print(f"\n{'─'*60}")
    print(f"Total new rows to import: {len(all_new):,}")
    by_ctry = all_new.groupby(['COUNTRY', 'YEAR', 'MONTH']).size()
    for keys, n in by_ctry.items():
        print(f"  {keys[0]:<12} {keys[1]} {keys[2]:<4}: {n:,} rows")

    if dry_run:
        print("\n[DRY RUN] No changes written.")
        return

    # Determine which (COUNTRY, YEAR, MONTH) periods to replace vs. just add.
    # Strategy: detect the "primary" import month — the year+month that accounts
    # for the majority of rows across all countries in the new data.
    # Stray rows from a different month (e.g. 2 late-March entries inside an
    # April file) are ADDITIVE — we do NOT wipe the existing March data.
    period_counts = all_new.groupby(['YEAR', 'MONTH']).size()
    primary_year, primary_month = period_counts.idxmax()
    print(f"\nPrimary import period detected: {primary_year} {primary_month} "
          f"({period_counts.max():,}/{len(all_new):,} rows)")

    # Only replace existing rows for the PRIMARY period (per country).
    # Rows for other periods in the new data are appended without clearing old data.
    primary_mask = (all_new['YEAR'] == primary_year) & (all_new['MONTH'] == primary_month)
    primary_countries = all_new.loc[primary_mask, 'COUNTRY'].unique()

    mask_remove = pd.Series(False, index=db.index)
    for ctry in primary_countries:
        mask_remove |= (
            (db['TYPE'].isin(['REAL', 'SCENARIO 2'])) &
            (db['COUNTRY'] == ctry) &
            (db['YEAR']    == primary_year) &
            (db['MONTH']   == primary_month)
        )
    n_removed = mask_remove.sum()
    if n_removed:
        print(f"Removing {n_removed:,} existing REAL/SCENARIO 2 rows for "
              f"{primary_year} {primary_month} (will be replaced) …")
    db = db[~mask_remove]

    # Build SCENARIO 2 copy (identical to REAL; TYPE = 'SCENARIO 2')
    scenario2 = all_new.copy()
    scenario2['TYPE'] = 'SCENARIO 2'

    # Append REAL + SCENARIO 2 new rows
    db_updated = pd.concat([db, all_new, scenario2], ignore_index=True)
    print(f"New total: {len(db_updated):,} rows  "
          f"(+{len(all_new):,} REAL, +{len(scenario2):,} SCENARIO 2)")

    # Save
    save_main_db(db_updated)

    # Regenerate dashboards
    print("\n" + "═"*60)
    print("Regenerating dashboards …")
    regenerate_dashboards()

    print("\n" + "═"*60)
    print("✔ Done! All dashboards updated.")
    if unrecognised:
        print(f"\n⚠  Skipped (unrecognised country): {[f.name for f in unrecognised]}")


# ──────────────────────────────────────────────────────────────────────────────
def collect_xlsx_from_folder(folder: Path) -> list[Path]:
    """Find all .xlsx files in folder whose name suggests a country sales file."""
    patterns = ['total sales', 'ventas', 'venda']
    files = []
    for fp in sorted(folder.glob('*.xlsx')):
        if any(p in fp.name.lower() for p in patterns):
            files.append(fp)
    return files


def show_menu():
    """Show the main menu and return the user's choice."""
    print("\n" + "="*60)
    print("  LATAM Dashboard — Data Update Tool")
    print("="*60)
    print("  1. Import new monthly files (e.g. MAY26 folder)")
    print("  2. Regenerate dashboards only")
    print("     (use this when you edited ANALISE Q1 2026 2.xlsx directly)")
    print("  0. Exit")
    print("="*60)
    return input("  Choice: ").strip()


def resolve_files_interactively(args: list[str], dry: bool, yes: bool = False) -> list[Path]:
    """Resolve source files, prompting the user if needed (supports double-click launch)."""
    while True:
        if not args:
            # Auto-detect files in BASE_DIR
            print(f"\nAuto-detecting monthly sales files in: {BASE_DIR}")
            files = collect_xlsx_from_folder(BASE_DIR)
            if not files:
                print("  No files found automatically.")
        elif len(args) == 1 and Path(args[0]).is_dir():
            folder = Path(args[0])
            print(f"Scanning folder: {folder}")
            files = collect_xlsx_from_folder(folder)
        else:
            files = [Path(a) for a in args]

        # Filter to existing files only
        missing = [f for f in files if not f.exists()]
        if missing:
            for f in missing:
                print(f"  File not found: {f}")
            files = [f for f in files if f.exists()]

        if files:
            print(f"\nFiles to process ({len(files)}):")
            for f in files:
                country = detect_country(f)
                print(f"  {f.name:<45} -> {country or '(unrecognised)'}")

        if not dry and not yes:
            if files:
                answer = input("\nProceed? [s/N] or type folder path for a different month: ").strip()
            else:
                answer = input("\nType the folder path with the monthly files (e.g. MAY26): ").strip()

            answer_lower = answer.lower()

            if answer_lower in ('s', 'y'):
                break  # confirmed — proceed with current files
            elif answer_lower in ('n', ''):
                # User said no — ask for a different folder
                folder_input = input("Type folder path (or press Enter to cancel): ").strip().strip('"')
                if not folder_input:
                    print("Cancelled.")
                    input("\nPressione Enter para fechar...")
                    sys.exit(0)
                args = [folder_input]  # retry with new folder
                continue
            elif answer:
                # User typed a path directly instead of s/N
                args = [answer.strip('"')]
                continue
            else:
                print("Cancelled.")
                input("\nPressione Enter para fechar...")
                sys.exit(0)
        else:
            break  # dry run or --yes — no confirmation needed

    return files


if __name__ == '__main__':
    try:
        args = [a for a in sys.argv[1:] if a not in ('--dry-run', '--yes')]
        dry  = '--dry-run' in sys.argv
        yes  = '--yes'     in sys.argv

        if dry:
            print("[DRY RUN MODE — no files will be written]\n")

        # If no args passed (double-click launch), show menu first
        if not args and not dry:
            choice = show_menu()
            if choice == '2':
                print("\nRegenerando dashboards...")
                regenerate_dashboards()
                print("\n✔ Dashboards atualizados!")
                input("\nPressione Enter para fechar...")
                sys.exit(0)
            elif choice == '0' or choice == '':
                print("Cancelled.")
                input("\nPressione Enter para fechar...")
                sys.exit(0)
            # choice == '1' falls through to file import below

        files = resolve_files_interactively(args, dry, yes=yes)
        run(files, dry_run=dry)

    except Exception as e:
        import traceback
        print("\n" + "="*60)
        print("ERRO:")
        traceback.print_exc()
        print("="*60)

    if sys.stdin.isatty():
        input("\nPressione Enter para fechar...")  # keep window open after double-click
