#!/usr/bin/env python3
"""
Generate LATAM Q1 2026 Dashboard HTML from Excel data.
Full rebuild with month-filter, all-English, 7 tabs.
"""
import pandas as pd
import json
import numpy as np
from pathlib import Path

BASE_DIR = Path(r"C:\Users\Soporte\OneDrive - Travel Blue\Ambiente de Trabalho\Dashboards Camila\travel-blue-dashboards\LATAM SALES_BP 26")
EXCEL = BASE_DIR / "ANALISE Q1 2026 2.xlsx"
OUTPUT = Path(r"C:\Users\Soporte\OneDrive - Travel Blue\Ambiente de Trabalho\Dashboards Camila\DASHBOARDS CAMINHO NOVO") / "Business Review LATAM 2026.html"

# ─────────────────────────── Constants ───────────────────────────────────────
COUNTRY_ORDER   = ['MEXICO','BRAZIL','ARGENTINA','COLOMBIA','PANAMA','CHILE','PERU']
SC2_COUNTRIES   = ['ARGENTINA','BRAZIL','PANAMA','MEXICO']
NON_SC2_COUNTRIES = ['COLOMBIA','CHILE','PERU']
YEARS_HIST      = [2018,2019,2020,2021,2022,2023,2024,2025]
MONTHS_PT       = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
MONTH_IDX       = {m: i for i, m in enumerate(MONTHS_PT)}
VALID_CHANNELS  = {'DOMESTIC','RETAIL','ONLINE','OTHER'}
BRAND4_ORDER    = ['TRAVEL BLUE','CLOE','LEXINGHAM+ANOMEO','OTHERS']

# ─────────────────────────── Load & Clean Data ───────────────────────────────
print("Reading Excel…")
df = pd.read_excel(EXCEL, sheet_name='SALES_SYSTEM_DATABASE')
print(f"  {len(df)} rows loaded.")

def fix_brand(b):
    if pd.isna(b): return 'OTHERS'
    s = str(b)
    if 'AN' in s and 'MEO' in s: return 'ANOMEO'
    return s

df['BRAND3_CLEAN'] = df['BRAND 3'].apply(fix_brand)
df['BRAND2_CLEAN'] = df['BRAND 2'].apply(fix_brand)

def brand4(b3):
    if b3 == 'TRAVEL BLUE': return 'TRAVEL BLUE'
    if b3 == 'CLOE': return 'CLOE'
    if b3 in ('LEXINGHAM','ANOMEO'): return 'LEXINGHAM+ANOMEO'
    return 'OTHERS'

df['BRAND4'] = df['BRAND3_CLEAN'].apply(brand4)

def brand2_clean_to_b2(b2):
    if b2 == 'TRAVEL BLUE': return 'TRAVEL BLUE'
    if b2 == 'CLOE': return 'CLOE'
    if b2 in ('LEXINGHAM','ANOMEO'): return 'LEXINGHAM+ANOMEO'
    return 'OTHERS'

# Ensure YEAR is int
df['YEAR'] = pd.to_numeric(df['YEAR'], errors='coerce').astype('Int64')
df = df[df['YEAR'].notna()].copy()
df['YEAR'] = df['YEAR'].astype(int)

# Ensure SKU 2 is always string (column has mixed int/str values)
df['SKU 2'] = df['SKU 2'].astype(str)

# Month index
df['midx'] = df['MONTH'].map(MONTH_IDX)
df = df[df['midx'].notna()].copy()
df['midx'] = df['midx'].astype(int)

amt = 'NET AMOUNT (USD)'

# ─────────────────────────── Build 3D monthly dicts ──────────────────────────
def build_3d(sub, dim_col):
    """year → midx → dim → usd"""
    result = {}
    grp = sub.groupby(['YEAR','midx', dim_col])[amt].sum()
    for (yr, mi, dim), val in grp.items():
        result.setdefault(int(yr), {}).setdefault(int(mi), {})[str(dim)] = round(float(val), 2)
    return result

def build_2d(sub, dim_col):
    """midx → dim → usd  (no year, for BP)"""
    result = {}
    grp = sub.groupby(['midx', dim_col])[amt].sum()
    for (mi, dim), val in grp.items():
        result.setdefault(int(mi), {})[str(dim)] = round(float(val), 2)
    return result

# Split by type — NO channel filter here so 2018-2023 historical data is preserved
real_df = df[df['TYPE'] == 'REAL'].copy()
bp_df   = df[df['TYPE'] == 'BP 26'].copy()
print("Building monthly country data…")
realM   = build_3d(real_df, 'COUNTRY')
bpM     = build_2d(bp_df,   'COUNTRY')

# Channel data: only rows with valid channels (2018-2023 have NaN channel → excluded, correct)
print("Building channel data…")
ch_filt_real = real_df[real_df['CHANNEL'].isin(VALID_CHANNELS)].copy()
ch_filt_bp   = bp_df[bp_df['CHANNEL'].isin(VALID_CHANNELS)].copy()
chReal  = build_3d(ch_filt_real, 'CHANNEL')
chBP    = build_2d(ch_filt_bp,   'CHANNEL')

print("Building brand2 data…")
b2Real  = build_3d(real_df, 'BRAND2_CLEAN')
b2BP    = build_2d(bp_df,   'BRAND2_CLEAN')

# All unique Brand 2 values sorted by 2025 sales desc; OTHERS always last
_b2_totals = real_df[real_df['YEAR']==2025].groupby('BRAND2_CLEAN')[amt].sum()
all_brand2 = [str(b) for b in _b2_totals.sort_values(ascending=False).index if str(b) != 'OTHERS']
all_brand2.append('OTHERS')

# Per-country brand2: use same build_4d — already done below as b2CReal

print("Building brand4 data…")
b4Real  = build_3d(real_df, 'BRAND4')
b4BP    = build_2d(bp_df,   'BRAND4')

print("Building brand4 × country data…")
def build_4d(sub, dim1, dim2):
    """year → midx → dim1 → dim2 → usd"""
    result = {}
    grp = sub.groupby(['YEAR','midx', dim1, dim2])[amt].sum()
    for (yr, mi, d1, d2), val in grp.items():
        result.setdefault(int(yr), {}).setdefault(int(mi), {}).setdefault(str(d1), {})[str(d2)] = round(float(val), 2)
    return result

def build_3d_bp(sub, dim1, dim2):
    """midx → dim1 → dim2 → usd (BP has no year)"""
    result = {}
    grp = sub.groupby(['midx', dim1, dim2])[amt].sum()
    for (mi, d1, d2), val in grp.items():
        result.setdefault(int(mi), {}).setdefault(str(d1), {})[str(d2)] = round(float(val), 2)
    return result

b4CReal = build_4d(real_df, 'COUNTRY', 'BRAND4')
b4CBP   = build_3d_bp(bp_df, 'COUNTRY', 'BRAND4')

print("Building per-country channel/family/brand2 data…")
chCReal = build_4d(ch_filt_real, 'COUNTRY', 'CHANNEL')
chCBP   = build_3d_bp(ch_filt_bp, 'COUNTRY', 'CHANNEL')

print("Building family data…")
def fix_family2(f):
    if pd.isna(f): return 'OTHERS'
    s = str(f)
    if 'AN' in s and 'MEO' in s: return 'ANOMEO'
    return s

real_df['FAM2'] = real_df['FAMILY 2'].apply(fix_family2)
bp_df['FAM2']   = bp_df['FAMILY 2'].apply(fix_family2)
famReal  = build_3d(real_df, 'FAM2')
famBP    = build_2d(bp_df,   'FAM2')
famCReal = build_4d(real_df, 'COUNTRY', 'FAM2')
famCBP   = build_3d_bp(bp_df, 'COUNTRY', 'FAM2')
b2CReal  = build_4d(real_df, 'COUNTRY', 'BRAND2_CLEAN')
b2CBP    = build_3d_bp(bp_df, 'COUNTRY', 'BRAND2_CLEAN')

print("Building SKU × country-group data…")
SKU_GROUPS_PY = {
    'MEXICO':    ['MEXICO'],
    'BRAZIL':    ['BRAZIL'],
    'ARGENTINA': ['ARGENTINA'],
    'COLOMBIA':  ['COLOMBIA'],
    'OTHERS':    ['CHILE','PERU','PANAMA'],
}
# Top 15 SKUs per group from 2025
r25_real = real_df[real_df['YEAR'] == 2025]
top_skus_by_group = {}
for grp_key, countries in SKU_GROUPS_PY.items():
    sub = r25_real[r25_real['COUNTRY'].isin(countries)]
    tops = list(sub.groupby('SKU 2')[amt].sum().nlargest(15).index)
    top_skus_by_group[grp_key] = [str(s) for s in tops]

# Monthly SKU data for top SKUs per group
def build_sku_real(sub):
    """grp → year → midx → sku → value"""
    result = {}
    for grp_key, countries in SKU_GROUPS_PY.items():
        top = set(top_skus_by_group[grp_key])
        g = sub[sub['COUNTRY'].isin(countries) & sub['SKU 2'].isin(top)]
        yr_dict = {}
        for (yr, mi, sku), val in g.groupby(['YEAR','midx','SKU 2'])[amt].sum().items():
            yr_dict.setdefault(int(yr), {}).setdefault(int(mi), {})[str(sku)] = round(float(val), 2)
        result[grp_key] = yr_dict
    return result

def build_sku_bp(sub):
    """grp → midx → sku → value"""
    result = {}
    for grp_key, countries in SKU_GROUPS_PY.items():
        top = set(top_skus_by_group[grp_key])
        g = sub[sub['COUNTRY'].isin(countries) & sub['SKU 2'].isin(top)]
        mi_dict = {}
        for (mi, sku), val in g.groupby(['midx','SKU 2'])[amt].sum().items():
            mi_dict.setdefault(int(mi), {})[str(sku)] = round(float(val), 2)
        result[grp_key] = mi_dict
    return result

skuReal = build_sku_real(real_df)
skuBP   = build_sku_bp(bp_df)

print("Building per-country SKU data…")
r25_real = real_df[real_df['YEAR'] == 2025]
top_skus_by_country = {}
for country in COUNTRY_ORDER:
    c_sub = r25_real[r25_real['COUNTRY'] == country]
    tops = list(c_sub.groupby('SKU 2')[amt].sum().nlargest(20).index)
    top_skus_by_country[country] = [str(s) for s in tops]

def build_sku_country_real(sub):
    result = {}
    for country in COUNTRY_ORDER:
        top = set(top_skus_by_country[country])
        g = sub[sub['COUNTRY'] == country].copy()
        g = g[g['SKU 2'].isin(top)]
        yr_dict = {}
        for (yr, mi, sku), val in g.groupby(['YEAR','midx','SKU 2'])[amt].sum().items():
            yr_dict.setdefault(int(yr), {}).setdefault(int(mi), {})[str(sku)] = round(float(val), 2)
        result[str(country)] = yr_dict
    return result

skuCReal = build_sku_country_real(real_df)

print("Building LATAM top-20 SKU data…")
r25_latam = real_df[real_df['YEAR'] == 2025]
top20_latam = [str(s) for s in r25_latam.groupby('SKU 2')[amt].sum().nlargest(20).index]

# Build comprehensive SKU → Brand + Category maps (all table SKUs)
all_table_skus = set(top20_latam)
for _tops in top_skus_by_country.values():
    all_table_skus.update(_tops)

sku_cat_map = {}
sku_brand_map = {}
for _sku in all_table_skus:
    _sub = real_df[real_df['SKU 2'] == _sku]
    _cat   = _sub['CATEGORY'].dropna().mode()
    _brand = _sub['BRAND 2'].dropna().mode()
    sku_cat_map[str(_sku)]   = str(_cat.iloc[0])   if len(_cat)   > 0 else '—'
    sku_brand_map[str(_sku)] = str(_brand.iloc[0]) if len(_brand) > 0 else '—'

def build_sku_latam_real(sub, top_skus):
    """year → midx → sku → value (LATAM-level, all countries)"""
    top = set(top_skus)
    result = {}
    g = sub[sub['SKU 2'].isin(top)]
    for (yr, mi, sku), val in g.groupby(['YEAR','midx','SKU 2'])[amt].sum().items():
        result.setdefault(int(yr), {}).setdefault(int(mi), {})[str(sku)] = round(float(val), 2)
    return result

skuLatamReal = build_sku_latam_real(real_df, top20_latam)

print("Building customer data…")
# Build per-country CUSTOMER→CUSTOMER3 correction map (BP-side takes priority per country,
# handles cases like Havan whose REAL rows have CUSTOMER3='OTHERS' but BP row has CUSTOMER3='HAVAN').
# Per-country maps prevent cross-country contamination (e.g. MERCADO LIBRE named in Mexico
# should not affect Brazil where MERCADO LIBRE rows have CUSTOMER3='OTHERS').
cu3_fix_map_per_country = {}
for _cty in COUNTRY_ORDER:
    _c_bp   = bp_df[bp_df['COUNTRY']==_cty]
    _c_real = real_df[real_df['COUNTRY']==_cty]
    _combo  = pd.concat([_c_bp[['CUSTOMER','CUSTOMER 3']], _c_real[['CUSTOMER','CUSTOMER 3']]]).copy()
    _combo['CUSTOMER']   = _combo['CUSTOMER'].astype(str)
    _combo['CUSTOMER 3'] = _combo['CUSTOMER 3'].astype(str)
    _named  = _combo[~_combo['CUSTOMER 3'].isin(['OTHERS','nan',''])]
    cu3_fix_map_per_country[_cty] = _named.groupby('CUSTOMER')['CUSTOMER 3'].first().to_dict()

# For the global LATAM top-15, build a combined map (cross-country merging is fine at LATAM level)
_cu3_global_combo = pd.concat([bp_df[['CUSTOMER','CUSTOMER 3']], real_df[['CUSTOMER','CUSTOMER 3']]]).copy()
_cu3_global_combo['CUSTOMER']   = _cu3_global_combo['CUSTOMER'].astype(str)
_cu3_global_combo['CUSTOMER 3'] = _cu3_global_combo['CUSTOMER 3'].astype(str)
_cu3_global_named = _cu3_global_combo[~_cu3_global_combo['CUSTOMER 3'].isin(['OTHERS','nan',''])]
cu3_fix_map_global = _cu3_global_named.groupby('CUSTOMER')['CUSTOMER 3'].first().to_dict()

# Apply global map for LATAM-wide CUST_KEY
real_df['CUST3_FIXED_GLOBAL'] = real_df['CUSTOMER'].astype(str).map(cu3_fix_map_global).fillna('OTHERS')
bp_df['CUST3_FIXED_GLOBAL']   = bp_df['CUSTOMER'].astype(str).map(cu3_fix_map_global).fillna('OTHERS')

# Top-15 real named customers (LATAM global, using global fixed mapping)
cust_totals = real_df[real_df['CUST3_FIXED_GLOBAL']!='OTHERS'].groupby('CUST3_FIXED_GLOBAL')[amt].sum().sort_values(ascending=False)
top15 = [str(c) for c in cust_totals.head(15).index]   # guaranteed no 'OTHERS'

def cust_key(c):
    return str(c) if str(c) in top15 else 'OTHERS'

real_df['CUST_KEY'] = real_df['CUST3_FIXED_GLOBAL'].apply(cust_key)
bp_df['CUST_KEY']   = bp_df['CUST3_FIXED_GLOBAL'].apply(cust_key)

cuReal = build_3d(real_df, 'CUST_KEY')
cuBP   = build_2d(bp_df,   'CUST_KEY')

# Per-country customer data: top 10 named customers per country (using per-country maps)
print("Building per-country customer data…")
top10_by_country = {}
for country in COUNTRY_ORDER:
    _fix = cu3_fix_map_per_country[country]
    c_sub = real_df[real_df['COUNTRY']==country].copy()
    c_sub['CUST3_FIXED_C'] = c_sub['CUSTOMER'].astype(str).map(_fix).fillna('OTHERS')
    tops = list(c_sub[c_sub['CUST3_FIXED_C']!='OTHERS'].groupby('CUST3_FIXED_C')[amt].sum().nlargest(10).index)
    top10_by_country[country] = [str(c) for c in tops]

def build_cust_country(sub):
    """country → year → midx → cust → value (uses per-country cu3 fix maps)"""
    result = {}
    for country in COUNTRY_ORDER:
        top_c = set(top10_by_country[country])
        _fix  = cu3_fix_map_per_country[country]
        c_sub = sub[sub['COUNTRY'] == country].copy()
        c_sub['CUST_C'] = c_sub['CUSTOMER'].astype(str).map(_fix).fillna('OTHERS')
        c_sub['CUST_C'] = c_sub['CUST_C'].apply(lambda x: str(x) if str(x) in top_c else 'OTHERS')
        yr_dict = {}
        for (yr, mi, cust), val in c_sub.groupby(['YEAR','midx','CUST_C'])[amt].sum().items():
            yr_dict.setdefault(int(yr), {}).setdefault(int(mi), {})[str(cust)] = round(float(val), 2)
        result[str(country)] = yr_dict
    return result

def build_cust_country_bp(sub):
    """country → midx → cust → value (uses per-country cu3 fix maps)"""
    result = {}
    for country in COUNTRY_ORDER:
        top_c = set(top10_by_country[country])
        _fix  = cu3_fix_map_per_country[country]
        c_sub = sub[sub['COUNTRY'] == country].copy()
        c_sub['CUST_C'] = c_sub['CUSTOMER'].astype(str).map(_fix).fillna('OTHERS')
        c_sub['CUST_C'] = c_sub['CUST_C'].apply(lambda x: str(x) if str(x) in top_c else 'OTHERS')
        mi_dict = {}
        for (mi, cust), val in c_sub.groupby(['midx','CUST_C'])[amt].sum().items():
            mi_dict.setdefault(int(mi), {})[str(cust)] = round(float(val), 2)
        result[str(country)] = mi_dict
    return result

cuCReal = build_cust_country(real_df)
cuCBP   = build_cust_country_bp(bp_df)

# ─────────────────────────── QTY parallel structures ─────────────────────────
print("Building QTY data structures…")
qty_col = 'QTY'

def build_3d_q(sub, dim_col):
    result = {}
    grp = sub.groupby(['YEAR','midx', dim_col])[qty_col].sum()
    for (yr, mi, dim), val in grp.items():
        result.setdefault(int(yr), {}).setdefault(int(mi), {})[str(dim)] = round(float(val), 2)
    return result

def build_2d_q(sub, dim_col):
    result = {}
    grp = sub.groupby(['midx', dim_col])[qty_col].sum()
    for (mi, dim), val in grp.items():
        result.setdefault(int(mi), {})[str(dim)] = round(float(val), 2)
    return result

def build_4d_q(sub, dim1, dim2):
    result = {}
    grp = sub.groupby(['YEAR','midx', dim1, dim2])[qty_col].sum()
    for (yr, mi, d1, d2), val in grp.items():
        result.setdefault(int(yr), {}).setdefault(int(mi), {}).setdefault(str(d1), {})[str(d2)] = round(float(val), 2)
    return result

def build_3d_bp_q(sub, dim1, dim2):
    result = {}
    grp = sub.groupby(['midx', dim1, dim2])[qty_col].sum()
    for (mi, d1, d2), val in grp.items():
        result.setdefault(int(mi), {}).setdefault(str(d1), {})[str(d2)] = round(float(val), 2)
    return result

realMQ    = build_3d_q(real_df, 'COUNTRY')
bpMQ      = build_2d_q(bp_df,   'COUNTRY')
chRealQ   = build_3d_q(ch_filt_real, 'CHANNEL')
chBPQ     = build_2d_q(ch_filt_bp,   'CHANNEL')
b4RealQ   = build_3d_q(real_df, 'BRAND4')
b4BPQ     = build_2d_q(bp_df,   'BRAND4')
famRealQ  = build_3d_q(real_df, 'FAM2')
famBPQ    = build_2d_q(bp_df,   'FAM2')
b2RealQ   = build_3d_q(real_df, 'BRAND2_CLEAN')
b2BPQ     = build_2d_q(bp_df,   'BRAND2_CLEAN')
cuRealQ   = build_3d_q(real_df, 'CUST_KEY')
cuBPQ     = build_2d_q(bp_df,   'CUST_KEY')
chCRealQ  = build_4d_q(ch_filt_real, 'COUNTRY', 'CHANNEL')
chCBPQ    = build_3d_bp_q(ch_filt_bp, 'COUNTRY', 'CHANNEL')
b4CRealQ  = build_4d_q(real_df, 'COUNTRY', 'BRAND4')
b4CBPQ    = build_3d_bp_q(bp_df, 'COUNTRY', 'BRAND4')
famCRealQ = build_4d_q(real_df, 'COUNTRY', 'FAM2')
famCBPQ   = build_3d_bp_q(bp_df, 'COUNTRY', 'FAM2')
b2CRealQ  = build_4d_q(real_df, 'COUNTRY', 'BRAND2_CLEAN')
b2CBPQ    = build_3d_bp_q(bp_df, 'COUNTRY', 'BRAND2_CLEAN')

def build_cust_country_q(sub):
    result = {}
    for country in COUNTRY_ORDER:
        top_c = set(top10_by_country[country])
        _fix  = cu3_fix_map_per_country[country]
        c_sub = sub[sub['COUNTRY'] == country].copy()
        c_sub['CUST_C'] = c_sub['CUSTOMER'].astype(str).map(_fix).fillna('OTHERS')
        c_sub['CUST_C'] = c_sub['CUST_C'].apply(lambda x: str(x) if str(x) in top_c else 'OTHERS')
        yr_dict = {}
        for (yr, mi, cust), val in c_sub.groupby(['YEAR','midx','CUST_C'])[qty_col].sum().items():
            yr_dict.setdefault(int(yr), {}).setdefault(int(mi), {})[str(cust)] = round(float(val), 2)
        result[str(country)] = yr_dict
    return result

def build_cust_country_bp_q(sub):
    result = {}
    for country in COUNTRY_ORDER:
        top_c = set(top10_by_country[country])
        _fix  = cu3_fix_map_per_country[country]
        c_sub = sub[sub['COUNTRY'] == country].copy()
        c_sub['CUST_C'] = c_sub['CUSTOMER'].astype(str).map(_fix).fillna('OTHERS')
        c_sub['CUST_C'] = c_sub['CUST_C'].apply(lambda x: str(x) if str(x) in top_c else 'OTHERS')
        mi_dict = {}
        for (mi, cust), val in c_sub.groupby(['midx','CUST_C'])[qty_col].sum().items():
            mi_dict.setdefault(int(mi), {})[str(cust)] = round(float(val), 2)
        result[str(country)] = mi_dict
    return result

cuCRealQ = build_cust_country_q(real_df)
cuCBPQ   = build_cust_country_bp_q(bp_df)

# ─── Small countries: raw CUSTOMER column, no OTHERS grouping ─────────────────
print("Building small-country customer data (raw CUSTOMER column)…")
_SMALL_C = ['ARGENTINA','COLOMBIA','CHILE','PANAMA','PERU']
_qty_sc   = 'QTY'
small_cu_tops = {}; small_cu_real_d = {}; small_cu_bp_d = {}
small_cu_real_q_d = {}; small_cu_bp_q_d = {}; small_cu_channel_d = {}

for _sc in _SMALL_C:
    _cr = real_df[real_df['COUNTRY'] == _sc].copy()
    _cb = bp_df[bp_df['COUNTRY'] == _sc].copy()
    _r25 = _cr[_cr['YEAR'] == 2025]
    _tops = [str(c) for c in _r25.groupby('CUSTOMER')[amt].sum().sort_values(ascending=False).index
             if str(c) not in ('nan','None','','OTHERS')]
    for _cu in _cr[_cr['YEAR']==2026]['CUSTOMER'].dropna().unique():
        if str(_cu) not in ('nan','None','','OTHERS') and str(_cu) not in _tops:
            _tops.append(str(_cu))
    small_cu_tops[_sc] = _tops
    _f = _cr[_cr['CUSTOMER'].notna()]
    _yr_r = {}
    for (yr,mi,cu),val in _f.groupby(['YEAR','midx','CUSTOMER'])[amt].sum().items():
        if str(cu) in ('nan','None',''): continue
        _yr_r.setdefault(int(yr),{}).setdefault(int(mi),{})[str(cu)] = round(float(val),2)
    small_cu_real_d[_sc] = _yr_r
    _mb = {}
    for (mi,cu),val in _cb[_cb['CUSTOMER'].notna()].groupby(['midx','CUSTOMER'])[amt].sum().items():
        if str(cu) in ('nan','None',''): continue
        _mb.setdefault(int(mi),{})[str(cu)] = round(float(val),2)
    small_cu_bp_d[_sc] = _mb
    _yr_rq = {}
    for (yr,mi,cu),val in _f.groupby(['YEAR','midx','CUSTOMER'])[_qty_sc].sum().items():
        if str(cu) in ('nan','None',''): continue
        _yr_rq.setdefault(int(yr),{}).setdefault(int(mi),{})[str(cu)] = round(float(val),2)
    small_cu_real_q_d[_sc] = _yr_rq
    _mbq = {}
    for (mi,cu),val in _cb[_cb['CUSTOMER'].notna()].groupby(['midx','CUSTOMER'])[_qty_sc].sum().items():
        if str(cu) in ('nan','None',''): continue
        _mbq.setdefault(int(mi),{})[str(cu)] = round(float(val),2)
    small_cu_bp_q_d[_sc] = _mbq
    for _cu in _tops:
        _sub = _cr[_cr['CUSTOMER'] == _cu]
        _ch = _sub['CHANNEL'].dropna().value_counts()
        small_cu_channel_d[_cu] = str(_ch.index[0]) if len(_ch) > 0 else '—'

# ─── Brand × Category × Customer matrix per country ──────────────────────────
print("Building brand×category×customer matrix…")
_SMALL_C_SET = set(_SMALL_C)
bcc_tops  = {}   # country → bc_key → [top10 customer names]
bccCReal  = {}   # country → year → midx → bc_key → customer → usd
bccCRealQ = {}   # country → year → midx → bc_key → customer → qty

for _cc in COUNTRY_ORDER:
    _cu_col = 'CUSTOMER'
    _cs = real_df[real_df['COUNTRY'] == _cc].copy()
    _cs['_BC'] = _cs['BRAND 2'].fillna('OTHERS').astype(str) + '|||' + _cs['CATEGORY'].fillna('OTHERS').astype(str)
    _r25c = _cs[_cs['YEAR'] == 2025]
    _tops_c = {}
    for _bck, _grp in _r25c.groupby('_BC'):
        _t = [str(x) for x in _grp.groupby(_cu_col)[amt].sum().nlargest(10).index
              if str(x) not in ('nan','None','','OTHERS')]
        if _t: _tops_c[str(_bck)] = _t
    for _bck, _grp in _cs[_cs['YEAR']==2026].groupby('_BC'):
        if str(_bck) not in _tops_c:
            _t = [str(x) for x in _grp.groupby(_cu_col)[amt].sum().nlargest(10).index
                  if str(x) not in ('nan','None','','OTHERS')]
            if _t: _tops_c[str(_bck)] = _t
    bcc_tops[_cc] = _tops_c
    _all_bcc_cu = {x for v in _tops_c.values() for x in v}
    _cs_f = _cs[_cs[_cu_col].isin(_all_bcc_cu)]
    _yr_u = {}
    for (yr,mi,bc,cu),val in _cs_f.groupby(['YEAR','midx','_BC',_cu_col])[amt].sum().items():
        _bcs,_cus=str(bc),str(cu)
        if _cus in _tops_c.get(_bcs,[]):
            _yr_u.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_bcs,{})[_cus]=round(float(val),2)
    bccCReal[_cc] = _yr_u
    _yr_q = {}
    for (yr,mi,bc,cu),val in _cs_f.groupby(['YEAR','midx','_BC',_cu_col])[qty_col].sum().items():
        _bcs,_cus=str(bc),str(cu)
        if _cus in _tops_c.get(_bcs,[]):
            _yr_q.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_bcs,{})[_cus]=round(float(val),2)
    bccCRealQ[_cc] = _yr_q

# ─── Customer × Brand hierarchy (top 10 customers per country) ────────────────
print("Building customer×brand×category hierarchy…")
cb_tops   = {}   # country → [top10 customer names by 2025 sales]
cbCReal   = {}   # country → year → midx → customer → brand → usd
cbCRealQ  = {}   # country → year → midx → customer → brand → qty
cbcTBCReal  = {}  # country → year → midx → customer → category → usd (TB only)
cbcTBCRealQ = {}  # country → year → midx → customer → category → qty (TB only)
cbcTBFamCReal  = {}  # country → year → midx → customer → family → usd (TB only)
cbcTBFamCRealQ = {}  # country → year → midx → customer → family → qty (TB only)
cbcTBFamCatCReal  = {}  # country → year → midx → customer → family → category → usd (TB only)
cbcTBFamCatCRealQ = {}  # country → year → midx → customer → family → category → qty (TB only)

for _cc2 in COUNTRY_ORDER:
    _cs2 = real_df[real_df['COUNTRY'] == _cc2].copy()
    _r25x = _cs2[_cs2['YEAR'] == 2025]
    _tops2 = [str(x) for x in _r25x.groupby('CUSTOMER')[amt].sum().nlargest(10).index
              if str(x) not in ('nan','None','','OTHERS')]
    for _cux in _cs2[_cs2['YEAR']==2026]['CUSTOMER'].dropna().unique():
        if str(_cux) not in ('nan','None','','OTHERS') and str(_cux) not in _tops2:
            _tops2.append(str(_cux))
    cb_tops[_cc2] = _tops2
    _cs2_f = _cs2[_cs2['CUSTOMER'].isin(set(_tops2))]
    # Customer × Brand USD
    _yr_cb = {}
    for (yr,mi,cu,b2),val in _cs2_f.groupby(['YEAR','midx','CUSTOMER','BRAND 2'])[amt].sum().items():
        _cu_s,_b2_s=str(cu),str(b2)
        if _cu_s in _tops2:
            _yr_cb.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_b2_s]=round(float(val),2)
    cbCReal[_cc2] = _yr_cb
    # Customer × Brand QTY
    _yr_cbq = {}
    for (yr,mi,cu,b2),val in _cs2_f.groupby(['YEAR','midx','CUSTOMER','BRAND 2'])[qty_col].sum().items():
        _cu_s,_b2_s=str(cu),str(b2)
        if _cu_s in _tops2:
            _yr_cbq.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_b2_s]=round(float(val),2)
    cbCRealQ[_cc2] = _yr_cbq
    # Customer × Travel Blue × Category USD
    _cs2_tb = _cs2_f[_cs2_f['BRAND 2'] == 'TRAVEL BLUE']
    _yr_cbc = {}
    for (yr,mi,cu,cat),val in _cs2_tb.groupby(['YEAR','midx','CUSTOMER','CATEGORY'])[amt].sum().items():
        _cu_s,_cat_s=str(cu),str(cat)
        if _cu_s in _tops2:
            _yr_cbc.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_cat_s]=round(float(val),2)
    cbcTBCReal[_cc2] = _yr_cbc
    # Customer × Travel Blue × Category QTY
    _yr_cbcq = {}
    for (yr,mi,cu,cat),val in _cs2_tb.groupby(['YEAR','midx','CUSTOMER','CATEGORY'])[qty_col].sum().items():
        _cu_s,_cat_s=str(cu),str(cat)
        if _cu_s in _tops2:
            _yr_cbcq.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_cat_s]=round(float(val),2)
    cbcTBCRealQ[_cc2] = _yr_cbcq
    # Customer × Travel Blue × FAMILY USD
    _yr_cbf = {}
    for (yr,mi,cu,fam),val in _cs2_tb.groupby(['YEAR','midx','CUSTOMER','FAMILY'])[amt].sum().items():
        _cu_s,_fam_s=str(cu),str(fam)
        if _cu_s in _tops2:
            _yr_cbf.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_fam_s]=round(float(val),2)
    cbcTBFamCReal[_cc2] = _yr_cbf
    # Customer × Travel Blue × FAMILY QTY
    _yr_cbfq = {}
    for (yr,mi,cu,fam),val in _cs2_tb.groupby(['YEAR','midx','CUSTOMER','FAMILY'])[qty_col].sum().items():
        _cu_s,_fam_s=str(cu),str(fam)
        if _cu_s in _tops2:
            _yr_cbfq.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_fam_s]=round(float(val),2)
    cbcTBFamCRealQ[_cc2] = _yr_cbfq
    # Customer × Travel Blue × FAMILY × CATEGORY USD
    _yr_cbfc = {}
    for (yr,mi,cu,fam,cat),val in _cs2_tb.groupby(['YEAR','midx','CUSTOMER','FAMILY','CATEGORY'])[amt].sum().items():
        _cu_s,_fam_s,_cat_s=str(cu),str(fam),str(cat)
        if _cu_s in _tops2:
            _yr_cbfc.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{}).setdefault(_fam_s,{})[_cat_s]=round(float(val),2)
    cbcTBFamCatCReal[_cc2] = _yr_cbfc
    # Customer × Travel Blue × FAMILY × CATEGORY QTY
    _yr_cbfcq = {}
    for (yr,mi,cu,fam,cat),val in _cs2_tb.groupby(['YEAR','midx','CUSTOMER','FAMILY','CATEGORY'])[qty_col].sum().items():
        _cu_s,_fam_s,_cat_s=str(cu),str(fam),str(cat)
        if _cu_s in _tops2:
            _yr_cbfcq.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{}).setdefault(_fam_s,{})[_cat_s]=round(float(val),2)
    cbcTBFamCatCRealQ[_cc2] = _yr_cbfcq

# ─── Customer → Channel map ───────────────────────────────────────────────────
print("Building customer-channel maps…")
cu_channel_map = {}
for _cu in top15:
    _sub = real_df[real_df['CUST3_FIXED_GLOBAL'] == _cu]  # use global fixed mapping (handles Havan)
    _ch_mode = _sub['CHANNEL'].dropna().value_counts()
    cu_channel_map[_cu] = str(_ch_mode.index[0]) if len(_ch_mode) > 0 else '—'

cu_channel_by_country = {}
for _country in COUNTRY_ORDER:
    _fix = cu3_fix_map_per_country[_country]
    for _cu in top10_by_country[_country]:
        # find rows for this country where CUSTOMER maps to this key (per-country)
        _sub = real_df[(real_df['COUNTRY']==_country) & (real_df['CUSTOMER'].astype(str).map(_fix).fillna('OTHERS') == _cu)]
        _ch_mode = _sub['CHANNEL'].dropna().value_counts()
        cu_channel_by_country[_cu] = str(_ch_mode.index[0]) if len(_ch_mode) > 0 else '—'

# ─── Travel Blue Top 20 SKUs ──────────────────────────────────────────────────
print("Building Travel Blue Top 20 SKUs…")
# Rank by 2026 Real sales (primary) — ensures table shows items with actual 2026 activity
r26_tb = real_df[(real_df['YEAR'] == 2026) & (real_df['BRAND 2'] == 'TRAVEL BLUE')]
r25_tb = real_df[(real_df['YEAR'] == 2025) & (real_df['BRAND 2'] == 'TRAVEL BLUE')]
top20_latam_tb = [str(s) for s in r26_tb.groupby('SKU 2')[amt].sum().nlargest(20).index]

top_tb_by_country = {}
for _country in COUNTRY_ORDER:
    _c_tb26 = r26_tb[r26_tb['COUNTRY'] == _country]
    _tops = list(_c_tb26.groupby('SKU 2')[amt].sum().nlargest(20).index)
    # If fewer than 20 SKUs in 2026, fill remaining slots with best 2025 SKUs not already included
    if len(_tops) < 20:
        _c_tb25 = r25_tb[r25_tb['COUNTRY'] == _country]
        _tops25 = [s for s in _c_tb25.groupby('SKU 2')[amt].sum().nlargest(20).index if str(s) not in [str(t) for t in _tops]]
        _tops = _tops + _tops25[:20 - len(_tops)]
    top_tb_by_country[_country] = [str(s) for s in _tops]

# Ensure TB SKUs are in cat/brand maps
_all_tb_skus = set(top20_latam_tb)
for _tops in top_tb_by_country.values():
    _all_tb_skus.update(_tops)
for _sku in _all_tb_skus - all_table_skus:
    _sub = real_df[real_df['SKU 2'] == _sku]
    _cat   = _sub['CATEGORY'].dropna().mode()
    _brand = _sub['BRAND 2'].dropna().mode()
    sku_cat_map[str(_sku)]   = str(_cat.iloc[0])   if len(_cat)   > 0 else '—'
    sku_brand_map[str(_sku)] = str(_brand.iloc[0]) if len(_brand) > 0 else '—'

skuLatamRealTB = build_sku_latam_real(real_df, top20_latam_tb)

def build_sku_country_real_filtered(sub, top_dict):
    result = {}
    for country in COUNTRY_ORDER:
        top = set(top_dict[country])
        if not top:
            result[str(country)] = {}
            continue
        g = sub[sub['COUNTRY'] == country].copy()
        g = g[g['SKU 2'].isin(top)]
        yr_dict = {}
        for (yr, mi, sku), val in g.groupby(['YEAR','midx','SKU 2'])[amt].sum().items():
            yr_dict.setdefault(int(yr), {}).setdefault(int(mi), {})[str(sku)] = round(float(val), 2)
        result[str(country)] = yr_dict
    return result

skuCRealTB = build_sku_country_real_filtered(real_df, top_tb_by_country)

def build_sku_latam_q(sub, top_skus):
    top = set(top_skus)
    result = {}
    g = sub[sub['SKU 2'].isin(top)]
    for (yr, mi, sku), val in g.groupby(['YEAR','midx','SKU 2'])[qty_col].sum().items():
        result.setdefault(int(yr), {}).setdefault(int(mi), {})[str(sku)] = round(float(val), 2)
    return result

def build_sku_country_q(sub, top_dict):
    result = {}
    for country in COUNTRY_ORDER:
        top = set(top_dict[country])
        if not top:
            result[str(country)] = {}
            continue
        g = sub[sub['COUNTRY'] == country].copy()
        g = g[g['SKU 2'].isin(top)]
        yr_dict = {}
        for (yr, mi, sku), val in g.groupby(['YEAR','midx','SKU 2'])[qty_col].sum().items():
            yr_dict.setdefault(int(yr), {}).setdefault(int(mi), {})[str(sku)] = round(float(val), 2)
        result[str(country)] = yr_dict
    return result

skuLatamRealQ   = build_sku_latam_q(real_df, top20_latam)
skuLatamRealTBQ = build_sku_latam_q(real_df, top20_latam_tb)
skuCRealQ       = build_sku_country_q(real_df, top_skus_by_country)
skuCRealTBQ     = build_sku_country_q(real_df, top_tb_by_country)

# ─────────────────────────── All-customer data (Vendas por Cliente tab) ──────
print("Building all-customer data per country for Vendas por Cliente tab…")
qty_col_cu = 'QTY'
allCuCReal  = {}   # country → year → midx → customer → value
allCuCRealQ = {}   # country → year → midx → customer → qty
allCuCList  = {}   # country → [customer list sorted by 2026 sales desc]
allCuCChannelMap = {}  # country → customer → channel
for _c in COUNTRY_ORDER:
    _r_c = real_df[real_df['COUNTRY']==_c].copy()
    _r_c['CUSTOMER'] = _r_c['CUSTOMER'].astype(str)
    _yr_usd = {}
    for (yr,mi,cu),v in _r_c.groupby(['YEAR','midx','CUSTOMER'])[amt].sum().items():
        _yr_usd.setdefault(int(yr),{}).setdefault(int(mi),{})[str(cu)] = round(float(v),2)
    allCuCReal[str(_c)] = _yr_usd
    _yr_qty = {}
    for (yr,mi,cu),v in _r_c.groupby(['YEAR','midx','CUSTOMER'])[qty_col_cu].sum().items():
        _yr_qty.setdefault(int(yr),{}).setdefault(int(mi),{})[str(cu)] = round(float(v),2)
    allCuCRealQ[str(_c)] = _yr_qty
    _r26_c = _r_c[_r_c['YEAR']==2026]
    _cu_list_26 = [str(c) for c in _r26_c.groupby('CUSTOMER')[amt].sum().sort_values(ascending=False).index]
    _cu_other = [str(c) for c in _r_c[_r_c['YEAR'].isin([2024,2025])].groupby('CUSTOMER')[amt].sum().sort_values(ascending=False).index if str(c) not in _cu_list_26]
    allCuCList[str(_c)] = _cu_list_26 + _cu_other
    _ch_map = {}
    for _cu, _grp in _r_c.groupby('CUSTOMER'):
        _ch = _grp['CHANNEL'].dropna().value_counts()
        _ch_map[str(_cu)] = str(_ch.index[0]) if len(_ch) > 0 else '—'
    allCuCChannelMap[str(_c)] = _ch_map

# ─────────────────────────── Embed flag images as base64 ─────────────────────
import urllib.request, base64 as _b64
_FLAG_CODES = {'MEXICO':'mx','BRAZIL':'br','ARGENTINA':'ar','COLOMBIA':'co','PANAMA':'pa','CHILE':'cl','PERU':'pe'}
flag_data_uris = {}
print("Fetching flag images…")
for _c, _code in _FLAG_CODES.items():
    try:
        _url = f'https://flagcdn.com/32x24/{_code}.png'
        with urllib.request.urlopen(_url, timeout=10) as _r:
            flag_data_uris[_c] = 'data:image/png;base64,' + _b64.b64encode(_r.read()).decode()
        print(f"  {_c} OK")
    except Exception as _e:
        flag_data_uris[_c] = ''
        print(f"  {_c} FAILED: {_e}")

# ─────────────────────── Load Scenario 2 file (replacement values) ───────────
print("Loading Scenario 2 data…")
SC2_FILE = BASE_DIR / "ANALISE Q1 2026 SCENARIO 2.xlsx"
sc2_raw = pd.read_excel(SC2_FILE, sheet_name='Planilha1')
sc2_raw = sc2_raw[sc2_raw['TYPE'] == 'SCENARIO 2'].copy()
sc2_raw['YEAR'] = pd.to_numeric(sc2_raw['YEAR'], errors='coerce')
sc2_raw = sc2_raw[sc2_raw['YEAR'].notna()].copy()
sc2_raw['YEAR'] = sc2_raw['YEAR'].astype(int)
# MONTH column is numeric 1-12; convert to 0-indexed
sc2_raw['midx'] = pd.to_numeric(sc2_raw['MONTH'], errors='coerce') - 1
sc2_raw = sc2_raw[sc2_raw['midx'].between(0, 11)].copy()
sc2_raw['midx'] = sc2_raw['midx'].astype(int)

# sc2M_py: year → midx → country → SC2 value (total, replaces real for that month)
sc2M_py = {}
for _, row in sc2_raw.iterrows():
    yr  = int(row['YEAR'])
    mi  = int(row['midx'])
    cty = str(row['COUNTRY'])
    val = float(row['NET AMOUNT (USD)']) if pd.notna(row['NET AMOUNT (USD)']) else 0.0
    sc2M_py.setdefault(yr, {}).setdefault(mi, {})[cty] = \
        sc2M_py.get(yr, {}).get(mi, {}).get(cty, 0) + val
print(f"  SC2 rows: {len(sc2_raw)}, countries: {sorted(sc2_raw['COUNTRY'].unique())}, years: {sorted(sc2_raw['YEAR'].unique())}")

# ─────────────────────────── SC2 Diff months ─────────────────────────────────
print("Computing SC2 diffs…")
sc2_diff = {}
for country in SC2_COUNTRIES:
    sc2_diff[country] = {}
    for year in YEARS_HIST + [2026]:
        diffs = []
        for mi in range(12):
            sc2_val = sc2M_py.get(year, {}).get(mi, {}).get(country)
            if sc2_val is not None:
                real_val = realM.get(year, {}).get(mi, {}).get(country, 0)
                if abs(sc2_val - real_val) > 0.01:
                    diffs.append(mi)
        if diffs:
            sc2_diff[country][str(year)] = diffs

# ─────────────────────────── JSON serialise ──────────────────────────────────
def to_js(name, obj):
    return f"const {name} = {json.dumps(obj, ensure_ascii=False)};"

js_data = "\n".join([
    to_js("realM",   realM),
    to_js("bpM",     bpM),
    to_js("sc2M",    sc2M_py),
    to_js("sc2Diff", sc2_diff),
    to_js("chReal",  chReal),
    to_js("chBP",    chBP),
    to_js("b2Real",  b2Real),
    to_js("b2BP",    b2BP),
    to_js("b4Real",  b4Real),
    to_js("b4BP",    b4BP),
    to_js("cuReal",  cuReal),
    to_js("cuBP",    cuBP),
    to_js("top15Customers", top15),
    to_js("cuCReal", cuCReal),
    to_js("cuCBP",   cuCBP),
    to_js("top10ByCountry", top10_by_country),
    to_js("b4CReal", b4CReal),
    to_js("b4CBP",   b4CBP),
    to_js("famReal", famReal),
    to_js("famBP",   famBP),
    to_js("skuReal", skuReal),
    to_js("skuBP",   skuBP),
    to_js("topSkusByGroup", top_skus_by_group),
    to_js("chCReal",  chCReal),
    to_js("chCBP",    chCBP),
    to_js("famCReal", famCReal),
    to_js("famCBP",   famCBP),
    to_js("b2CReal",  b2CReal),
    to_js("b2CBP",    b2CBP),
    to_js("skuCReal", skuCReal),
    to_js("topSkusByCountry", top_skus_by_country),
    to_js("top20Latam", top20_latam),
    to_js("skuCatMap",   sku_cat_map),
    to_js("skuBrandMap", sku_brand_map),
    to_js("skuLatamReal", skuLatamReal),
    to_js("allBrand2", all_brand2),
    to_js("FLAG_URIS", flag_data_uris),
    # QTY parallel structures
    to_js("realMQ",    realMQ),
    to_js("bpMQ",      bpMQ),
    to_js("chRealQ",   chRealQ),
    to_js("chBPQ",     chBPQ),
    to_js("b4RealQ",   b4RealQ),
    to_js("b4BPQ",     b4BPQ),
    to_js("famRealQ",  famRealQ),
    to_js("famBPQ",    famBPQ),
    to_js("b2RealQ",   b2RealQ),
    to_js("b2BPQ",     b2BPQ),
    to_js("cuRealQ",   cuRealQ),
    to_js("cuBPQ",     cuBPQ),
    to_js("chCRealQ",  chCRealQ),
    to_js("chCBPQ",    chCBPQ),
    to_js("b4CRealQ",  b4CRealQ),
    to_js("b4CBPQ",    b4CBPQ),
    to_js("famCRealQ", famCRealQ),
    to_js("famCBPQ",   famCBPQ),
    to_js("b2CRealQ",  b2CRealQ),
    to_js("b2CBPQ",    b2CBPQ),
    to_js("cuCRealQ",  cuCRealQ),
    to_js("cuCBPQ",    cuCBPQ),
    # Customer channel maps
    to_js("cuChannelMap",        cu_channel_map),
    to_js("cuChannelByCountry",  cu_channel_by_country),
    # Travel Blue SKUs
    to_js("top20LatamTB",   top20_latam_tb),
    to_js("topTBByCountry", top_tb_by_country),
    to_js("skuLatamRealTB", skuLatamRealTB),
    to_js("skuCRealTB",     skuCRealTB),
    to_js("skuLatamRealQ",   skuLatamRealQ),
    to_js("skuLatamRealTBQ", skuLatamRealTBQ),
    to_js("skuCRealQ",       skuCRealQ),
    to_js("skuCRealTBQ",     skuCRealTBQ),
    to_js("smallCuTops",       small_cu_tops),
    to_js("smallCuCReal",      small_cu_real_d),
    to_js("smallCuCBP",        small_cu_bp_d),
    to_js("smallCuCRealQ",     small_cu_real_q_d),
    to_js("smallCuCBPQ",       small_cu_bp_q_d),
    to_js("smallCuChannelMap", small_cu_channel_d),
    to_js("bccTops",   bcc_tops),
    to_js("bccCReal",  bccCReal),
    to_js("bccCRealQ", bccCRealQ),
    to_js("cbTops",      cb_tops),
    to_js("cbCReal",     cbCReal),
    to_js("cbCRealQ",    cbCRealQ),
    to_js("cbcTBCReal",  cbcTBCReal),
    to_js("cbcTBCRealQ", cbcTBCRealQ),
    to_js("cbcTBFamCReal",  cbcTBFamCReal),
    to_js("cbcTBFamCRealQ", cbcTBFamCRealQ),
    to_js("cbcTBFamCatCReal",  cbcTBFamCatCReal),
    to_js("cbcTBFamCatCRealQ", cbcTBFamCatCRealQ),
    # All-customer data for Vendas por Cliente sub-tab
    to_js("allCuCReal",  allCuCReal),
    to_js("allCuCRealQ", allCuCRealQ),
    to_js("allCuCList",  allCuCList),
    to_js("allCuCChannelMap", allCuCChannelMap),
])

print("Building HTML…")

# ─────────────────────────── HTML Template ───────────────────────────────────
html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>LATAM Q1 2026 Sales Dashboard</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-datalabels/2.2.0/chartjs-plugin-datalabels.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<style>
:root{
  --bg:#0a0e1a;--card:#111827;--border:#1e293b;--text:#e2e8f0;--accent:#f59e0b;
  --hdr:#0d1424;--tab-active:#f59e0b;--tbl-head:#1e293b;--total-bg:#1e3a2e;--total-clr:#34d399;
  --muted:#94a3b8;--green:#10b981;--red:#ef4444;--blue:#3b82f6;
}
.light-mode{
  --bg:#f1f4f9;--card:#fff;--border:#dde3ec;--text:#1e293b;--accent:#113d85;
  --hdr:#113d85;--tab-active:#113d85;--tbl-head:#113d85;--total-bg:#dcfce7;--total-clr:#166534;
  --muted:#64748b;--green:#15803d;--red:#b91c1c;--blue:#1d4ed8;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
/* Header */
.hdr{background:var(--hdr);padding:12px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
.hdr-title{font-size:1.1rem;font-weight:700;color:var(--accent);white-space:nowrap}
.hdr-kpis{display:flex;gap:16px;flex-wrap:wrap}
.kpi-item{text-align:center}
.kpi-label{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.kpi-val{font-size:.95rem;font-weight:700;color:var(--text)}
.kpi-pct{font-size:.8rem;font-weight:600}
.pct-pos{color:var(--green)}.pct-neg{color:var(--red)}.pct-neu{color:var(--muted)}
.hdr-actions{display:flex;gap:8px;align-items:center}
.btn-theme{background:transparent;border:1px solid var(--border);color:var(--text);border-radius:6px;padding:4px 10px;cursor:pointer;font-size:.8rem}
.btn-theme:hover{background:var(--border)}
/* Month filter strip */
.month-strip{background:var(--hdr);border-bottom:1px solid var(--border);padding:8px 20px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;position:sticky;top:57px;z-index:99}
.month-strip-label{font-size:.7rem;color:var(--muted);text-transform:uppercase;margin-right:4px;white-space:nowrap}
.mth-btn{padding:3px 10px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.75rem;transition:all .15s}
.mth-btn.active{background:var(--accent);color:#000;border-color:var(--accent);font-weight:600}
.mth-btn:hover:not(.active){border-color:var(--accent);color:var(--accent)}
.strip-ctrl{display:flex;gap:4px;margin-left:4px}
.strip-ctrl button{padding:2px 8px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.7rem}
.strip-ctrl button:hover{border-color:var(--accent);color:var(--accent)}
/* Tabs */
.tabs-bar{display:flex;gap:0;border-bottom:1px solid var(--border);background:var(--hdr);padding:0 20px;overflow-x:auto;position:sticky;top:97px;z-index:98}
.tab-btn{display:flex;align-items:center;gap:6px;padding:10px 16px;cursor:pointer;border:none;background:transparent;color:var(--muted);font-size:.85rem;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s}
.tab-btn.active{color:var(--tab-active);border-bottom-color:var(--tab-active);font-weight:600}
.tab-btn:hover:not(.active){color:var(--text)}
.tab-content{display:none;padding:20px;max-width:100%;overflow-x:hidden}.tab-content.active{display:block}
/* Cards */
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px}
.card-sm{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px}
/* Summary grid */
.summary-latam{margin-bottom:14px}
/* LATAM hero card */
.latam-hero{background:linear-gradient(120deg,rgba(245,158,11,.12),rgba(59,130,246,.08));border:2px solid #f59e0b;border-radius:14px;padding:18px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:16px;width:100%;box-sizing:border-box}
.latam-flag-big{font-size:2.8rem;line-height:1}
.latam-title-blk .latam-name{font-size:1.25rem;font-weight:800;color:#f59e0b;letter-spacing:-.5px}
.latam-title-blk .latam-sub{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.8px}
.hero-metric{text-align:center;min-width:100px;flex:1 1 110px;padding:10px 14px;border-radius:10px;background:rgba(255,255,255,.04)}
.hero-metric-lbl{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.hero-metric-val{font-size:1.5rem;font-weight:800;color:var(--text);line-height:1.1}
.hero-metric-pct{display:inline-block;margin-top:5px;padding:2px 10px;border-radius:20px;font-size:.78rem;font-weight:700}
.hero-metric-pct.pos{background:rgba(16,185,129,.2);color:#10b981}
.hero-metric-pct.neg{background:rgba(239,68,68,.2);color:#ef4444}
.hero-metric-pct.neu{color:var(--muted);font-size:.72rem}
/* Country grid — 7 cards in one full-width row */
.country-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;margin-top:0}
@media(max-width:1100px){.country-grid{grid-template-columns:repeat(4,1fr)}}
@media(max-width:650px){.country-grid{grid-template-columns:repeat(2,1fr)}}
.country-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 12px;cursor:default;transition:border-color .15s,transform .15s;display:flex;flex-direction:column;gap:8px}
.insights-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.insight-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:4px}
.insight-label{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.insight-val{font-size:1.1rem;font-weight:800;color:var(--text)}
.insight-sub{font-size:.75rem;color:var(--muted)}
.progress-wrap{margin-top:6px;background:rgba(255,255,255,.08);border-radius:4px;height:5px;overflow:hidden}
.progress-bar{height:5px;border-radius:4px;transition:width .4s}
.hist-kpis{display:flex;gap:14px;padding:5px 8px;background:rgba(255,255,255,.03);border-radius:6px;margin-top:4px;flex-wrap:wrap}
.hist-kpi-item{display:flex;align-items:center;gap:4px;font-size:.73rem}
.hist-kpi-lbl{color:var(--muted)}.hist-kpi-val{font-weight:700}
.hist-kpi-val.pos{color:var(--green)}.hist-kpi-val.neg{color:var(--red)}.hist-kpi-val.neu{color:var(--muted)}
.cc-share{font-size:.72rem;color:var(--accent);font-weight:700;text-align:right}
.country-card:hover{border-color:#f59e0b;transform:translateY(-2px)}
.cc-top{display:flex;align-items:center;gap:6px;border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:2px}
.cc-flag{font-size:1.5rem}.cc-name{font-weight:700;font-size:.82rem;color:var(--text);letter-spacing:.3px}
.cc-real-val{font-size:1.35rem;font-weight:800;color:#f59e0b;line-height:1}
.cc-real-lbl{font-size:.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px}
.cc-row{display:flex;justify-content:space-between;align-items:center;font-size:.75rem}
.cc-lbl{color:var(--muted);white-space:nowrap;flex-shrink:0}.cc-val{font-weight:600;color:var(--text);white-space:nowrap;text-align:right}
/* Charts area */
.chart-wrap{position:relative;width:100%;min-height:220px}
.chart-wrap canvas{max-height:320px}
.chart-grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:700px){.chart-grid-2{grid-template-columns:1fr}}
.section-title{font-size:.9rem;font-weight:600;color:var(--accent);margin-bottom:12px;padding-bottom:4px;border-bottom:1px solid var(--border)}
/* Tables */
.tbl-wrap{overflow-x:hidden}
table{width:100%;border-collapse:collapse;font-size:.72rem;table-layout:fixed}
th{background:var(--tbl-head);color:#fff;padding:6px 7px;text-align:right;white-space:normal;word-break:break-word;position:sticky;top:0;line-height:1.2}
.light-mode th{color:#fff}
th:first-child{text-align:left;width:22%}
td{padding:5px 7px;border-bottom:1px solid var(--border);text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
td:first-child{text-align:left}
tr:hover td{background:rgba(255,255,255,.03)}
tr.total-row td{background:var(--total-bg);color:var(--total-clr);font-weight:700}
.light-mode tr.total-row td{background:var(--total-bg);color:var(--total-clr)}
.pill{display:inline-block;padding:1px 6px;border-radius:10px;font-size:.72rem;font-weight:600}
.pill.pos{background:#064e3b;color:#34d399}.pill.neg{background:#450a0a;color:#fca5a5}
.light-mode .pill.pos{background:#dcfce7;color:#166534}.light-mode .pill.neg{background:#fee2e2;color:#b91c1c}
/* SC2 detail table */
.sc2-detail{margin-top:8px;overflow-x:auto}
.sc2-detail table{font-size:.72rem}
.sc2-detail th{font-size:.7rem;background:var(--border);color:var(--text)}
.sc2-legend{font-size:.7rem;color:var(--muted);margin-top:4px}
.sc2-legend span{display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b;margin-right:4px;vertical-align:middle}
/* Spacing helpers */
.mb16{margin-bottom:16px}.mb8{margin-bottom:8px}.mt12{margin-top:12px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:16px;min-width:0}.row2>.card{min-width:0;overflow:hidden}
@media(max-width:600px){.row2{grid-template-columns:1fr}}
.row4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:900px){.row4{grid-template-columns:repeat(2,1fr)}}
@media(max-width:500px){.row4{grid-template-columns:1fr}}
/* Country pill bar */
.country-pill-bar{display:flex;gap:8px;flex-wrap:wrap;padding:14px 0 8px}
.cpill{padding:5px 16px;border-radius:20px;border:2px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.8rem;font-weight:600;transition:all .15s}
.cpill.active{background:var(--accent);color:#000;border-color:var(--accent)}
.cpill:hover:not(.active){border-color:var(--accent);color:var(--accent)}
/* Sub-tab bar */
.sub-tabs-bar{display:flex;gap:0;border-bottom:2px solid var(--border);margin-bottom:16px}
.sub-tab-btn{padding:8px 18px;border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:.83rem;border-bottom:2px solid transparent;margin-bottom:-2px;display:flex;align-items:center;gap:5px;transition:all .15s;white-space:nowrap}
.sub-tab-btn.active{color:var(--accent);border-bottom-color:var(--accent);font-weight:600}
.sub-tab-btn:hover:not(.active){color:var(--text)}
/* Summary card adjustments */
.cc-real-val{font-size:1.05rem;font-weight:800;color:#f59e0b;line-height:1.3;word-break:break-all}
.country-card{min-height:170px;font-size:.78rem}
.cc-row{font-size:.72rem}
/* Flag images — all use same style, size set inline */
img.flag-img,
.cc-top img, .cpill img, .section-title img, td img, th img {
  border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.35);
  vertical-align:middle;flex-shrink:0
}
/* View mode toggle */
.view-toggle{display:flex;gap:3px;margin-left:8px}
.vbtn{padding:3px 11px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.72rem;transition:all .15s;white-space:nowrap}
.vbtn.active{background:var(--accent);color:#000;border-color:var(--accent);font-weight:700}
.vbtn:hover:not(.active){border-color:var(--accent);color:var(--accent)}
/* NEW pill */
.pill.new-item{background:#1e3a5f;color:#60a5fa}
.light-mode .pill.new-item{background:#dbeafe;color:#1d4ed8}
</style>
</head>
<body>
<!-- HEADER -->
<div class="hdr">
  <div class="hdr-title">🌎 LATAM Sales &amp; BP 2026</div>
  <div class="hdr-kpis" id="hdrKpis"></div>
  <div class="hdr-actions">
    <button class="btn-theme" onclick="toggleTheme()"><i class="bi bi-circle-half"></i> Theme</button>
  </div>
</div>

<!-- MONTH FILTER STRIP -->
<div class="month-strip">
  <span class="month-strip-label"><i class="bi bi-calendar3"></i> Months:</span>
  <div id="monthBtns" style="display:flex;gap:5px;flex-wrap:wrap"></div>
  <div class="strip-ctrl">
    <button onclick="selectAllMonths()">All</button>
    <button onclick="clearAllMonths()">Clear</button>
  </div>
  <div class="view-toggle" style="margin-left:16px">
    <button class="vbtn active" id="vbtnUSD" onclick="setViewMode('usd')"><i class="bi bi-currency-dollar"></i> USD</button>
    <button class="vbtn" id="vbtnQTY" onclick="setViewMode('qty')"><i class="bi bi-box-seam"></i> QTY</button>
    <button class="vbtn" id="vbtnAVG" onclick="setViewMode('avg')"><i class="bi bi-calculator"></i> AVG</button>
  </div>
  <button id="pdfBtn" onclick="exportPDF()" style="margin-left:auto;padding:3px 13px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.72rem;display:flex;align-items:center;gap:5px;white-space:nowrap;transition:all .15s" onmouseover="this.style.borderColor='var(--accent)';this.style.color='var(--accent)'" onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--muted)'">
    <i class="bi bi-file-earmark-pdf"></i> Export PDF
  </button>
</div>

<!-- TABS BAR -->
<div class="tabs-bar" id="tabsBar">
  <button class="tab-btn active" data-tab="summary" onclick="switchTab('summary',this)"><i class="bi bi-grid"></i> Summary</button>
  <button class="tab-btn" data-tab="historical" onclick="switchTab('historical',this)"><i class="bi bi-graph-up-arrow"></i> Historical</button>
  <button class="tab-btn" data-tab="annual" onclick="switchTab('annual',this)"><i class="bi bi-bar-chart-stacked"></i> Annual by Country</button>
  <button class="tab-btn" data-tab="period" onclick="switchTab('period',this)"><i class="bi bi-water"></i> Period Comparison</button>
  <button class="tab-btn" data-tab="country" onclick="switchTab('country',this)"><i class="bi bi-pin-map-fill"></i> Country Analysis</button>
  <button class="tab-btn" data-tab="latamdetail" onclick="switchTab('latamdetail',this)"><i class="bi bi-table"></i> LATAM Detail</button>
</div>

<!-- TAB CONTENTS -->
<div id="tab-summary" class="tab-content active">
  <div class="summary-latam mb16" id="latamCard"></div>
  <div class="country-grid mb16" id="countryGrid"></div>
  <div class="row2 mb16">
    <div class="card">
      <div class="section-title">Country Performance — 2026 Real vs 2025 vs BP</div>
      <div class="chart-wrap" style="height:320px"><canvas id="chSumBars"></canvas></div>
    </div>
    <div class="card" style="overflow:hidden;min-width:0">
      <div class="section-title">2026 Real — Market Share by Country</div>
      <div class="chart-wrap" style="height:340px;max-width:100%;overflow:hidden"><canvas id="chSumDonut"></canvas></div>
    </div>
  </div>
</div>
<div id="tab-historical" class="tab-content">
  <div class="card mb16">
    <div class="section-title">LATAM Total — Historical Real vs BP</div>
    <div class="chart-wrap"><canvas id="chHistLatam"></canvas></div>
    <div id="histKpiLatam"></div>
  </div>
  <div class="chart-grid-2 mb16" id="histCountryCharts"></div>
  <div class="card mb16">
    <div class="section-title">LATAM Scenario 2 — Historical</div>
    <div class="chart-wrap"><canvas id="chHistLatamSC2"></canvas></div>
  </div>
  <div class="chart-grid-2" id="histSC2Charts"></div>
</div>
<div id="tab-annual" class="tab-content">
  <div class="row2 mb16">
    <div class="card">
      <div class="section-title">Annual by Country — Absolute ($K)</div>
      <div class="chart-wrap"><canvas id="chAnnualAbs"></canvas></div>
    </div>
    <div class="card">
      <div class="section-title">Annual by Country — % Mix</div>
      <div class="chart-wrap"><canvas id="chAnnualPct"></canvas></div>
    </div>
  </div>
  <div class="card"><div class="tbl-wrap" id="annualTable"></div></div>
</div>
<div id="tab-period" class="tab-content">
  <div class="row2 mb16">
    <div class="card">
      <div class="section-title">Period Comparison by Country</div>
      <div class="chart-wrap"><canvas id="chPeriodGrouped"></canvas></div>
    </div>
    <div class="card">
      <div class="section-title">Waterfall: 2025 → 2026 Real → BP</div>
      <div class="chart-wrap"><canvas id="chWaterfall"></canvas></div>
    </div>
  </div>
</div>
<div id="tab-country" class="tab-content">
  <div class="country-pill-bar" id="countryPillBar"></div>
  <div class="sub-tabs-bar">
    <button class="sub-tab-btn active" data-sub="channels" onclick="switchSubTab('channels',this)"><i class="bi bi-shop"></i> Channels</button>
    <button class="sub-tab-btn" data-sub="customers" onclick="switchSubTab('customers',this)"><i class="bi bi-people-fill"></i> Customers</button>
    <button class="sub-tab-btn" data-sub="salescust" onclick="switchSubTab('salescust',this)"><i class="bi bi-table"></i> Sales / Customer</button>
    <button class="sub-tab-btn" data-sub="custbrand" onclick="switchSubTab('custbrand',this)"><i class="bi bi-diagram-3-fill"></i> Customer — Brand</button>
    <button class="sub-tab-btn" data-sub="brands" onclick="switchSubTab('brands',this)"><i class="bi bi-tags-fill"></i> Brands</button>
    <button class="sub-tab-btn" data-sub="family" onclick="switchSubTab('family',this)"><i class="bi bi-grid-3x3-gap-fill"></i> Family</button>
    <button class="sub-tab-btn" data-sub="products" onclick="switchSubTab('products',this)"><i class="bi bi-upc-scan"></i> Products</button>
  </div>
  <div id="countryContent"></div>
</div>
<div id="tab-latamdetail" class="tab-content">
  <div id="ldContent"></div>
</div>

<script>
// ── DATA ───────────────────────────────────────────────────────────────────
""" + js_data + r"""

// ── CONSTANTS ───────────────────────────────────────────────────────────────
const YEARS_HIST = [2018,2019,2020,2021,2022,2023,2024,2025];
const ALL_YEARS  = [2018,2019,2020,2021,2022,2023,2024,2025,2026];
const MONTHS_EN  = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const COUNTRY_ORDER = ['MEXICO','BRAZIL','ARGENTINA','COLOMBIA','PANAMA','CHILE','PERU'];
const SC2_COUNTRIES = ['ARGENTINA','BRAZIL','PANAMA','MEXICO'];
const NON_SC2_COUNTRIES = ['COLOMBIA','CHILE','PERU'];
const COUNTRY_COLORS = {MEXICO:'#f59e0b',BRAZIL:'#10b981',ARGENTINA:'#3b82f6',COLOMBIA:'#8b5cf6',PANAMA:'#ef4444',CHILE:'#f97316',PERU:'#06b6d4'};
const COUNTRY_FLAGS  = {MEXICO:'🇲🇽',BRAZIL:'🇧🇷',ARGENTINA:'🇦🇷',COLOMBIA:'🇨🇴',PANAMA:'🇵🇦',CHILE:'🇨🇱',PERU:'🇵🇪'};
// FLAG_URIS is injected from Python — base64 encoded flag images, fully offline
// Returns an <img> flag tag using embedded data URI
function flagImg(c) {
  const src = FLAG_URIS[c] || '';
  if (!src) return '';
  return `<img src="${src}" alt="${c}" style="width:22px;height:16px;vertical-align:middle;margin-right:5px;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.35)">`;
}
// For Chart.js labels (images can't render inside charts — plain country name)
const COUNTRY_LABELS = COUNTRY_ORDER.map(c => c);
const SC2_EFFECTS    = {ARGENTINA:'Exchange Rate Effect',BRAZIL:'Unicross Brand Effect',PANAMA:'Month Billing Adjustment',MEXICO:'Maxell Brand Effect'};
const BRAND4_ORDER   = ['TRAVEL BLUE','CLOE','LEXINGHAM+ANOMEO','OTHERS'];
const BRAND4_COLORS  = {'TRAVEL BLUE':'#3b82f6','CLOE':'#f59e0b','LEXINGHAM+ANOMEO':'#10b981','OTHERS':'#94a3b8'};
const BRAND_YEARS    = [2024, 2025];
const CHANNELS       = ['DOMESTIC','RETAIL','ONLINE','OTHER'];
const CHANNEL_COLORS = {DOMESTIC:'#3b82f6',RETAIL:'#10b981',ONLINE:'#f59e0b',OTHER:'#94a3b8'};
const FAM2_ORDER     = ['CLOE','PILLOWS','SLOOTH','BACKPACKS','TRAVEL ACCESSORIES','SECURITY','OEM','LUGGAGE','LEXINGHAM','ANOMEO','OTHERS'];
// allBrand2 is injected from Python — all unique Brand 2 values sorted by 2025 sales, OTHERS last
const SKU_GROUP_KEYS   = ['MEXICO','BRAZIL','ARGENTINA','COLOMBIA','OTHERS'];
const SKU_GROUP_LABELS = ['\uD83C\uDDF2\uD83C\uDDFD Mexico','\uD83C\uDDE7\uD83C\uDDF7 Brazil','\uD83C\uDDE6\uD83C\uDDF7 Argentina','\uD83C\uDDE8\uD83C\uDDF4 Colombia','\uD83C\uDF0E Others'];
const SKU_GROUP_COUNTRIES = {MEXICO:['MEXICO'],BRAZIL:['BRAZIL'],ARGENTINA:['ARGENTINA'],COLOMBIA:['COLOMBIA'],OTHERS:['CHILE','PERU','PANAMA']};

// Register datalabels plugin
Chart.register(ChartDataLabels);

// ── COLORS (explicit hex — CSS vars don't work inside Chart.js configs) ───────
let COLORS = { grid:'#1e293b', tick:'#94a3b8', text:'#e2e8f0', legendTxt:'#e2e8f0', totalLbl:'#f59e0b' };
function refreshColors() {
  const dark = !document.body.classList.contains('light-mode');
  COLORS.grid      = dark ? '#1e293b' : '#e2e8f0';
  COLORS.tick      = dark ? '#94a3b8' : '#64748b';
  COLORS.text      = dark ? '#e2e8f0' : '#1e293b';
  COLORS.legendTxt = dark ? '#e2e8f0' : '#1e293b';
  COLORS.totalLbl  = '#f59e0b';
}

// ── STATE ───────────────────────────────────────────────────────────────────
let selectedMonths = [0,1,2,3,4,5,6,7,8,9]; // Default: Jan-Oct (YTD)
let tabDirty = {historical:true, annual:true, period:true, country:true, latamdetail:true};
let charts = {};
let currentTab       = 'summary';
let currentCountry   = 'MEXICO';
let currentSubTab    = 'channels';
let viewMode         = 'usd'; // 'usd' | 'qty' | 'avg'

function setViewMode(m) {
  viewMode = m;
  ['USD','QTY','AVG'].forEach(x => {
    const b = document.getElementById('vbtn'+x);
    if (b) b.classList.toggle('active', x.toLowerCase() === m);
  });
  updateAll();
}
// Format value based on viewMode: usd=dollar, qty=pieces, avg=$/pcs
function fmtV(usd, qty) {
  if (viewMode === 'qty') return (qty==null||isNaN(qty)) ? '—' : Math.round(qty).toLocaleString('en-US') + ' pcs';
  if (viewMode === 'avg') return (qty>0 && usd!=null && !isNaN(usd)) ? '$'+(usd/qty).toFixed(2) : '—';
  return fmt(usd);
}
function fmtVK(usd, qty) {
  if (viewMode === 'qty') return (qty==null||isNaN(qty)) ? '' : Math.round(qty).toLocaleString('en-US');
  if (viewMode === 'avg') return (qty>0 && usd!=null) ? '$'+(usd/qty).toFixed(2) : '';
  return fmtK(usd);
}
function fmtChartLbl(v) {
  if (v == null || isNaN(v) || v === 0) return '';
  if (viewMode === 'qty') {
    const a = Math.abs(v);
    return a >= 1000000 ? (v/1000000).toFixed(1)+'M' : a >= 1000 ? (v/1000).toFixed(0)+'K' : Math.round(v).toString();
  }
  if (viewMode === 'avg') return '$'+v.toFixed(2);
  const a = Math.abs(v);
  return a >= 1000000 ? '$'+(v/1000000).toFixed(1)+'M' : '$'+Math.round(v/1000)+'K';
}
function fmtChartTooltip(v) {
  if (v == null || isNaN(v)) return '—';
  if (viewMode === 'qty') return Math.round(v).toLocaleString('en-US')+' pcs';
  if (viewMode === 'avg') return '$'+v.toFixed(2);
  return '$'+Math.round(v).toLocaleString('en-US');
}
// QTY aggregate helpers
function sumRealQ(year, months, country) {
  const yd = realMQ[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[country]||0), 0);
}
function sumBPQ(months, country) {
  return months.reduce((s,mi) => s + ((bpMQ[mi]||{})[country]||0), 0);
}
function sumLatamQ(year, months) {
  return COUNTRY_ORDER.reduce((s,c) => s + sumRealQ(year, months, c), 0);
}
function sumLatamBPQ(months) {
  return COUNTRY_ORDER.reduce((s,c) => s + sumBPQ(months, c), 0);
}
function sumDimQ(dataObj, year, months, dim) {
  const yd = dataObj[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[dim]||0), 0);
}
function sumDimBPQ(bpObj, months, dim) {
  return months.reduce((s,mi) => s + ((bpObj[mi]||{})[dim]||0), 0);
}
function sumChanCQ(country, year, months, channel) {
  const yd = chCRealQ[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[country])||{})[channel]||0), 0);
}
function sumChanCBPQ(country, months, channel) {
  return months.reduce((s,mi) => s + ((((chCBPQ[mi]||{})[country])||{})[channel]||0), 0);
}
function sumB4CQ(year, months, country, brand) {
  const yd = b4CRealQ[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[country])||{})[brand]||0), 0);
}
function sumB4CBPQ(months, country, brand) {
  return months.reduce((s,mi) => s + ((((b4CBPQ[mi]||{})[country])||{})[brand]||0), 0);
}
function sumFamCQ(country, year, months, fam) {
  const yd = famCRealQ[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[country])||{})[fam]||0), 0);
}
function sumFamCBPQ(country, months, fam) {
  return months.reduce((s,mi) => s + ((((famCBPQ[mi]||{})[country])||{})[fam]||0), 0);
}
function sumB2CQ(country, year, months, brand) {
  const yd = b2CRealQ[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[country])||{})[brand]||0), 0);
}
function sumB2CBPQ(country, months, brand) {
  return months.reduce((s,mi) => s + ((((b2CBPQ[mi]||{})[country])||{})[brand]||0), 0);
}
function sumCuCQ(country, year, months, cust) {
  const cd = (cuCRealQ[country] || {})[year] || {};
  return months.reduce((s,mi) => s + ((cd[mi]||{})[cust]||0), 0);
}
function sumCuCBPQ(country, months, cust) {
  const cd = cuCBPQ[country] || {};
  return months.reduce((s,mi) => s + ((cd[mi]||{})[cust]||0), 0);
}
function sumSkuLatamTB(year, months, sku) {
  const yd = skuLatamRealTB[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[sku]||0), 0);
}
function sumSkuLatamQ(year, months, sku) {
  const yd = skuLatamRealQ[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[sku]||0), 0);
}
function sumSkuLatamTBQ(year, months, sku) {
  const yd = skuLatamRealTBQ[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[sku]||0), 0);
}
function sumSkuCTB(country, year, months, sku) {
  const yd = (skuCRealTB[country]||{})[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[sku]||0), 0);
}
function sumSkuCQ(country, year, months, sku) {
  const yd = (skuCRealQ[country]||{})[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[sku]||0), 0);
}
function sumSkuCTBQ(country, year, months, sku) {
  const yd = (skuCRealTBQ[country]||{})[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[sku]||0), 0);
}
function sumCbC(country,year,months,cu,brand) {
  const yd=(cbCReal[country]||{})[year]||{};
  return months.reduce((s,mi)=>s+((((yd[mi]||{})[cu])||{})[brand]||0),0);
}
function sumCbCQ(country,year,months,cu,brand) {
  const yd=(cbCRealQ[country]||{})[year]||{};
  return months.reduce((s,mi)=>s+((((yd[mi]||{})[cu])||{})[brand]||0),0);
}
function sumCbcTBC(country,year,months,cu,cat) {
  const yd=(cbcTBCReal[country]||{})[year]||{};
  return months.reduce((s,mi)=>s+((((yd[mi]||{})[cu])||{})[cat]||0),0);
}
function sumCbcTBCQ(country,year,months,cu,cat) {
  const yd=(cbcTBCRealQ[country]||{})[year]||{};
  return months.reduce((s,mi)=>s+((((yd[mi]||{})[cu])||{})[cat]||0),0);
}
function sumCuTotalCb(country,year,months,cu) {
  const yd=(cbCReal[country]||{})[year]||{};
  return months.reduce((s,mi)=>{const bd=(yd[mi]||{})[cu]||{};return s+Object.values(bd).reduce((a,b)=>a+b,0);},0);
}
function sumCuTotalCbQ(country,year,months,cu) {
  const yd=(cbCRealQ[country]||{})[year]||{};
  return months.reduce((s,mi)=>{const bd=(yd[mi]||{})[cu]||{};return s+Object.values(bd).reduce((a,b)=>a+b,0);},0);
}
function getBrandsForCu(country,cu) {
  const brands=new Set();
  const cData=cbCReal[country]||{};
  Object.values(cData).forEach(yd=>Object.values(yd).forEach(md=>Object.keys(md[cu]||{}).forEach(b=>brands.add(b))));
  return [...brands];
}
function getCatsForCuTB(country,cu) {
  const cats=new Set();
  const cData=cbcTBCReal[country]||{};
  Object.values(cData).forEach(yd=>Object.values(yd).forEach(md=>Object.keys(md[cu]||{}).forEach(c=>cats.add(c))));
  return [...cats];
}
function sumCbcTBFam(country,year,months,cu,fam) {
  const yd=(cbcTBFamCReal[country]||{})[year]||{};
  return months.reduce((s,mi)=>s+((((yd[mi]||{})[cu])||{})[fam]||0),0);
}
function sumCbcTBFamQ(country,year,months,cu,fam) {
  const yd=(cbcTBFamCRealQ[country]||{})[year]||{};
  return months.reduce((s,mi)=>s+((((yd[mi]||{})[cu])||{})[fam]||0),0);
}
function getFamsForCuTB(country,cu) {
  const fams=new Set();
  const cData=cbcTBFamCReal[country]||{};
  Object.values(cData).forEach(yd=>Object.values(yd).forEach(md=>Object.keys(md[cu]||{}).forEach(f=>fams.add(f))));
  return [...fams];
}
function sumCbcTBFamCat(country,year,months,cu,fam,cat) {
  const yd=(cbcTBFamCatCReal[country]||{})[year]||{};
  return months.reduce((s,mi)=>s+(((((yd[mi]||{})[cu])||{})[fam]||{})[cat]||0),0);
}
function sumCbcTBFamCatQ(country,year,months,cu,fam,cat) {
  const yd=(cbcTBFamCatCRealQ[country]||{})[year]||{};
  return months.reduce((s,mi)=>s+(((((yd[mi]||{})[cu])||{})[fam]||{})[cat]||0),0);
}
function getCatsForFam(country,cu,fam) {
  const cats=new Set();
  const cData=cbcTBFamCatCReal[country]||{};
  Object.values(cData).forEach(yd=>Object.values(yd).forEach(md=>{
    const famData=(md[cu]||{})[fam]||{};
    Object.keys(famData).forEach(c=>cats.add(c));
  }));
  return [...cats];
}
function sumBccC(country, year, months, bc, cu) {
  const yd = (bccCReal[country]||{})[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[bc])||{})[cu]||0), 0);
}
function sumBccCQ(country, year, months, bc, cu) {
  const yd = (bccCRealQ[country]||{})[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[bc])||{})[cu]||0), 0);
}
// Returns the display value for current viewMode given usd+qty aggregates
function getV(usd, qty) {
  return viewMode==='qty' ? qty : viewMode==='avg' ? (qty>0?usd/qty:0) : usd;
}
// pctPill with NEW support: handles zero/missing reference
function pctPillSafe(v26, v25, v24) {
  v24=v24||0;
  if (!v25 || Math.abs(v25) < 0.01) {
    if (v26 > 0 && Math.abs(v24) < 0.01) return '<span class="pill new-item">NEW</span>';
    return '<span class="pill" style="background:transparent;color:var(--muted)">—</span>';
  }
  return pctPill(safePct(v26, v25));
}
function pctPillSafeBP(v26, vBP) {
  if (!vBP || Math.abs(vBP) < 0.01) return '<span class="pill" style="background:transparent;color:var(--muted)">—</span>';
  return pctPill(safePct(v26, vBP));
}
// Tight threshold for granular tables (Customer-Brand hierarchy) — any non-zero prior value shows %
function pctPillTight(v26, v25, v24) {
  v24=v24||0;
  if (!v25 || Math.abs(v25) < 0.01) {
    if (v26 > 0 && Math.abs(v24) < 0.01) return '<span class="pill new-item">NEW</span>';
    return '<span class="pill" style="background:transparent;color:var(--muted)">—</span>';
  }
  return pctPill(((v26 - v25) / Math.abs(v25) * 100).toFixed(1));
}

// ── HELPERS ─────────────────────────────────────────────────────────────────
function sumReal(year, months, country) {
  const yd = realM[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[country]||0), 0);
}
function sumBP(months, country) {
  return months.reduce((s,mi) => s + ((bpM[mi]||{})[country]||0), 0);
}
function sumSC2(year, months, country) {
  // sc2M holds REPLACEMENT values; fall back to real when month/country not in sc2M
  const yd = sc2M[year] || {};
  return months.reduce((s,mi) => {
    const md = yd[mi] || {};
    return s + (country in md ? md[country] : (((realM[year]||{})[mi]||{})[country]||0));
  }, 0);
}
function sumSC2BP(months, country) {
  // BP under SC2 = standard BP (no change to BP under this scenario)
  return sumBP(months, country);
}
function sumLatam(year, months) {
  return COUNTRY_ORDER.reduce((s,c) => s + sumReal(year, months, c), 0);
}
function sumLatamSC2(year, months) {
  return SC2_COUNTRIES.reduce((s,c) => s + sumSC2(year, months, c), 0)
       + NON_SC2_COUNTRIES.reduce((s,c) => s + sumReal(year, months, c), 0);
}
function sumLatamSC2BP(months) {
  return sumLatamBP(months);
}
function sumLatamBP(months) {
  return COUNTRY_ORDER.reduce((s,c) => s + sumBP(months, c), 0);
}
function sumDim(dataObj, year, months, dim) {
  const yd = dataObj[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[dim]||0), 0);
}
function sumDimBP(bpObj, months, dim) {
  return months.reduce((s,mi) => s + ((bpObj[mi]||{})[dim]||0), 0);
}
function safePct(num, den) {
  if (Math.abs(den) < 0.01) return null;
  return ((num - den) / den * 100).toFixed(1);
}
function fmt(v) {
  if (v == null || isNaN(v)) return '—';
  return '$' + Math.round(v).toLocaleString('en-US');
}
function fmtK(v) {
  if (v == null || isNaN(v)) return '';
  return '$' + Math.round(v/1000).toLocaleString('en-US') + 'K';
}
function fmtInt(v) {
  if (v == null || isNaN(v)) return '—';
  return '$' + Math.round(v).toLocaleString('en-US');
}
function fmtSigned(delta) {
  if (delta == null || isNaN(delta)) return '';
  const sign = delta >= 0 ? '+' : '-';
  return sign + '$' + Math.round(Math.abs(delta)).toLocaleString('en-US');
}
// Tooltip helpers — value: $1,234,567 | pct: 12.3%
function mkTooltip(isPercent) {
  return {
    mode: 'index', intersect: false,
    callbacks: {
      label: ctx => {
        const lbl = ctx.dataset.label || '';
        if (lbl === '_total' || lbl === 'Base') return null;
        const v = ctx.raw;
        if (v == null || isNaN(v)) return null;
        if (isPercent) return ` ${lbl}: ${(+v).toFixed(1)}%`;
        return ` ${lbl}: ${fmtChartTooltip(v)}`;
      }
    }
  };
}
const stdTooltipCbk = mkTooltip(false).callbacks;
function pctPill(pct, tag='span') {
  if (pct == null) return '<span class="pill" style="background:transparent;color:var(--muted)">—</span>';
  const cls = parseFloat(pct) >= 0 ? 'pos' : 'neg';
  const sign = parseFloat(pct) >= 0 ? '+' : '';
  return `<${tag} class="pill ${cls}">${sign}${pct}%</${tag}>`;
}
function pctBadge(pct) {
  if (pct == null) return '<span class="kpi-pct pct-neu">—</span>';
  const cls = parseFloat(pct) >= 0 ? 'pct-pos' : 'pct-neg';
  const sign = parseFloat(pct) >= 0 ? '+' : '';
  return `<span class="kpi-pct ${cls}">${sign}${pct}%</span>`;
}
function sc2HasAdjInSelected(country, year) {
  const diff = (sc2Diff[country]||{})[String(year)]||[];
  return diff.some(mi => selectedMonths.includes(mi));
}

// ── THEME ────────────────────────────────────────────────────────────────────
function toggleTheme() {
  document.body.classList.toggle('light-mode');
  refreshColors();
  // Destroy and re-render all active charts so colors update
  Object.keys(charts).forEach(id => { if(charts[id]) { charts[id].destroy(); charts[id]=null; } });
  Object.keys(tabDirty).forEach(t => { tabDirty[t] = true; });
  if (currentTab === 'summary') renderSummary();
  else switchTab(currentTab, document.querySelector('.tab-btn.active'));
}

// ── MONTH FILTER ─────────────────────────────────────────────────────────────
function buildMonthButtons() {
  const container = document.getElementById('monthBtns');
  container.innerHTML = '';
  MONTHS_EN.forEach((m, i) => {
    const btn = document.createElement('button');
    btn.className = 'mth-btn' + (selectedMonths.includes(i) ? ' active' : '');
    btn.textContent = m;
    btn.dataset.mi = i;
    btn.onclick = () => toggleMonth(i, btn);
    container.appendChild(btn);
  });
}
function toggleMonth(mi, btn) {
  const idx = selectedMonths.indexOf(mi);
  if (idx >= 0) { selectedMonths.splice(idx, 1); btn.classList.remove('active'); }
  else { selectedMonths.push(mi); selectedMonths.sort((a,b)=>a-b); btn.classList.add('active'); }
  updateAll();
}
function selectAllMonths() {
  selectedMonths = [0,1,2,3,4,5,6,7,8,9,10,11];
  buildMonthButtons(); updateAll();
}
function clearAllMonths() {
  selectedMonths = [];
  buildMonthButtons(); updateAll();
}
function updateAll() {
  renderKPIs();
  if (currentTab === 'summary') renderSummary();
  else if (currentTab === 'historical') updateHistorical();
  else if (currentTab === 'annual') updateAnnual();
  else if (currentTab === 'period') updatePeriod();
  else if (currentTab === 'country') renderCountryContent();
  else if (currentTab === 'latamdetail') renderLDContent();
  // Mark other tabs dirty
  Object.keys(tabDirty).forEach(t => { if(t !== currentTab) tabDirty[t] = true; });
}

// ── TABS ─────────────────────────────────────────────────────────────────────
function switchTab(tab, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  btn.classList.add('active');
  currentTab = tab;
  if (tab === 'summary') renderSummary();
  else if (tab === 'historical') { if(tabDirty.historical) renderHistorical(); else updateHistorical(); }
  else if (tab === 'annual') { if(tabDirty.annual) renderAnnual(); else updateAnnual(); }
  else if (tab === 'period') { if(tabDirty.period) renderPeriod(); else updatePeriod(); }
  else if (tab === 'country') renderCountryTab();
  else if (tab === 'latamdetail') { renderLatamDetailTab(); }
  tabDirty[tab] = false;
}
function switchSubTab(sub, btn) {
  document.querySelectorAll('.sub-tab-btn').forEach(el => el.classList.remove('active'));
  btn.classList.add('active');
  currentSubTab = sub;
  renderCountryContent();
}

// ── KPIs ─────────────────────────────────────────────────────────────────────
function renderKPIs() {
  const r26 = sumLatam(2026, selectedMonths);
  const r25 = sumLatam(2025, selectedMonths);
  const bp  = sumLatamBP(selectedMonths);
  const pct25 = safePct(r26, r25);
  const pctBP = safePct(r26, bp);
  document.getElementById('hdrKpis').innerHTML = `
    <div class="kpi-item"><div class="kpi-label">LATAM 2026 Real</div><div class="kpi-val">${fmt(r26)}</div></div>
    <div class="kpi-item"><div class="kpi-label">2025 Same Period</div><div class="kpi-val">${fmt(r25)}</div></div>
    <div class="kpi-item"><div class="kpi-label">vs 2025</div>${pctBadge(pct25)}</div>
    <div class="kpi-item"><div class="kpi-label">BP 2026</div><div class="kpi-val">${fmt(bp)}</div></div>
    <div class="kpi-item"><div class="kpi-label">vs BP</div>${pctBadge(pctBP)}</div>
  `;
}

// ── SUMMARY TAB ───────────────────────────────────────────────────────────────
function renderSummary() {
  const r26 = sumLatam(2026, selectedMonths);
  const r25 = sumLatam(2025, selectedMonths);
  const bp  = sumLatamBP(selectedMonths);
  const p25 = safePct(r26, r25), pBP = safePct(r26, bp);
  const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const periodLabel = selectedMonths.length === 0 ? '2026'
    : selectedMonths.length === 12 ? 'Full Year 2026'
    : (selectedMonths.length === 1
        ? MONTH_NAMES[selectedMonths[0]] + ' 2026'
        : MONTH_NAMES[selectedMonths[0]] + '–' + MONTH_NAMES[selectedMonths[selectedMonths.length-1]] + ' 2026');
  function heroPct(pct) {
    if (pct == null) return `<span class="hero-metric-pct neu">\u2014</span>`;
    const cls = pct >= 0 ? 'pos' : 'neg';
    const sign = pct >= 0 ? '+' : '';
    return `<span class="hero-metric-pct ${cls}">${sign}${pct}%</span>`;
  }
  document.getElementById('latamCard').innerHTML = `
    <div class="latam-hero">
      <div class="latam-flag-big">🌎</div>
      <div class="latam-title-blk">
        <div class="latam-name">LATAM TOTAL</div>
        <div class="latam-sub">${periodLabel}</div>
      </div>
      <div class="hero-metric">
        <div class="hero-metric-lbl">2026 Real</div>
        <div class="hero-metric-val">${fmtInt(r26)}</div>
      </div>
      <div class="hero-metric">
        <div class="hero-metric-lbl">vs 2025</div>
        <div class="hero-metric-val">${fmtInt(r25)}</div>
        ${heroPct(p25)}
      </div>
      <div class="hero-metric">
        <div class="hero-metric-lbl">vs BP 2026</div>
        <div class="hero-metric-val">${fmtInt(bp)}</div>
        ${heroPct(pBP)}
      </div>
    </div>`;
  const grid = document.getElementById('countryGrid');
  grid.innerHTML = '';
  const latam26total = sumLatam(2026, selectedMonths);
  COUNTRY_ORDER.forEach(c => {
    const cr26 = sumReal(2026, selectedMonths, c);
    const cr25 = sumReal(2025, selectedMonths, c);
    const cbp  = sumBP(selectedMonths, c);
    const cp25 = safePct(cr26, cr25), cpBP = safePct(cr26, cbp);
    const share = latam26total > 0 ? (cr26/latam26total*100).toFixed(1) : '0.0';
    const div = document.createElement('div');
    div.className = 'country-card';
    div.innerHTML = `
      <div class="cc-top">${flagImg(c)}<span class="cc-name">${c}</span><span class="cc-share" style="margin-left:auto">${share}%</span></div>
      <div class="cc-real-lbl">2026 Real</div>
      <div class="cc-real-val">${fmtInt(cr26)}</div>
      <div class="cc-row"><span class="cc-lbl">vs 2025</span><span class="cc-val">${fmtInt(cr25)} ${pctPill(cp25)}</span></div>
      <div class="cc-row"><span class="cc-lbl">vs BP</span><span class="cc-val">${fmtInt(cbp)} ${pctPill(cpBP)}</span></div>`;
    grid.appendChild(div);
  });

  // ── Summary charts ───────────────────────────────────────────────────────────
  const vals26 = COUNTRY_ORDER.map(c => getV(sumReal(2026, selectedMonths, c), sumRealQ(2026, selectedMonths, c)));
  const vals25 = COUNTRY_ORDER.map(c => getV(sumReal(2025, selectedMonths, c), sumRealQ(2025, selectedMonths, c)));
  const valsBP = COUNTRY_ORDER.map(c => getV(sumBP(selectedMonths, c), sumBPQ(selectedMonths, c)));

  // Grouped bar — performance by country
  destroyChart('chSumBars');
  const barEl = document.getElementById('chSumBars');
  if (barEl) {
    barEl.style.height = '320px';
    charts.chSumBars = new Chart(barEl, {
      type: 'bar',
      data: {
        labels: COUNTRY_ORDER.map(c => c),
        datasets: [
          { label: '2025',      data: vals25, backgroundColor: '#3b82f699',
            datalabels: { display: ctx => ctx.dataset.data[ctx.dataIndex] > 30000,
              anchor:'end', align:'top', font:{size:7,weight:'600'}, formatter: v => fmtChartLbl(v), color:'#93c5fd', textShadowBlur:2, textShadowColor:'rgba(0,0,0,.8)' } },
          { label: '2026 Real', data: vals26, backgroundColor: '#f59e0bcc',
            datalabels: { display: ctx => ctx.dataset.data[ctx.dataIndex] > 15000,
              anchor:'end', align:'top', font:{size:8,weight:'700'}, formatter: v => fmtChartLbl(v), color:'#fcd34d', textShadowBlur:2, textShadowColor:'rgba(0,0,0,.8)' } },
          { label: 'BP 2026',   data: valsBP, backgroundColor: '#10b98166',
            datalabels: { display: ctx => ctx.dataset.data[ctx.dataIndex] > 30000,
              anchor:'end', align:'top', font:{size:7,weight:'600'}, formatter: v => fmtChartLbl(v), color:'#6ee7b7', textShadowBlur:2, textShadowColor:'rgba(0,0,0,.8)' } }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: COLORS.text, font: { size: 11 } } },
          tooltip: mkTooltip(false)
        },
        scales: {
          x: { ticks: { color: COLORS.tick, font: { size: 11 } }, grid: { color: COLORS.grid } },
          y: { ticks: { color: COLORS.tick, font: { size: 10 }, callback: v => fmtChartLbl(v) }, grid: { color: COLORS.grid } }
        }
      }
    });
  }

  // Doughnut — market share
  destroyChart('chSumDonut');
  const donutEl = document.getElementById('chSumDonut');
  if (donutEl) {
    donutEl.style.height = '340px';
    const donutColors = COUNTRY_ORDER.map(c => COUNTRY_COLORS[c]);
    charts.chSumDonut = new Chart(donutEl, {
      type: 'doughnut',
      data: {
        labels: COUNTRY_ORDER,
        datasets: [{ data: vals26, backgroundColor: donutColors, borderWidth: 2, borderColor: 'var(--card)' }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '58%',
        layout: { padding: 8 },
        plugins: {
          legend: { position: 'right',
            labels: { color: COLORS.text, font: { size: 8 }, padding: 5, boxWidth: 9, boxHeight: 9,
              generateLabels: chart => chart.data.labels.map((lbl, i) => {
                const v = chart.data.datasets[0].data[i];
                const total = chart.data.datasets[0].data.reduce((a,b)=>a+b,0);
                const pct = total > 0 ? (v/total*100).toFixed(1) : '0.0';
                return { text: `${lbl}  ${pct}%`, fillStyle: donutColors[i], strokeStyle: donutColors[i], fontColor: COLORS.text, hidden: false, index: i, datasetIndex: 0 };
              })
            }
          },
          tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${fmtChartTooltip(ctx.raw)} (${latam26total>0?(ctx.raw/latam26total*100).toFixed(1):'0'}%)` } },
          datalabels: {
            display: ctx => { const t = ctx.dataset.data.reduce((a,b)=>a+b,0); return t>0 && ctx.dataset.data[ctx.dataIndex]/t >= 0.10; },
            formatter: (v, ctx) => { const t = ctx.dataset.data.reduce((a,b)=>a+b,0); return t>0 ? (v/t*100).toFixed(1)+'%' : ''; },
            color: '#fff', font: { size: 9, weight: '700' }, textShadowBlur: 3, textShadowColor: 'rgba(0,0,0,.7)',
            clamp: true, clip: true }
        }
      }
    });
  }

}

// ── CHART HELPERS ─────────────────────────────────────────────────────────────
function defaultDLPlugin(color) {
  return {
    display: true,
    anchor: 'end', align: 'top',
    font: { size: 10 },
    formatter: v => (v && Math.abs(v) > 0) ? fmtChartLbl(v) : null,
    color: color || function(ctx){ return ctx.dataset.borderColor || '#e2e8f0'; }
  };
}
function noLabelPlugin() {
  return { display: false };
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); charts[id] = null; }
}
function histKpiHtml(v26, v25, vBP) {
  const p25 = safePct(v26, v25), pBP = safePct(v26, vBP);
  const pc = p => p === null ? '<span class="hist-kpi-val neu">—</span>'
    : `<span class="hist-kpi-val ${+p>=0?'pos':'neg'}">${+p>=0?'+':''}${p}%</span>`;
  return `<div class="hist-kpis"><span class="hist-kpi-item"><span class="hist-kpi-lbl">vs 2025:</span>${pc(p25)}</span><span class="hist-kpi-item"><span class="hist-kpi-lbl">vs BP:</span>${pc(pBP)}</span></div>`;
}

function lineChartCfg(labels, datasets, title) {
  return {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: COLORS.text, font:{size:11} } },
        tooltip: mkTooltip(false),
        datalabels: defaultDLPlugin()
      },
      scales: {
        x: { ticks:{color:COLORS.tick,font:{size:10}}, grid:{color:COLORS.grid} },
        y: { ticks:{color:COLORS.tick,font:{size:10}, callback: v => fmtChartLbl(v)}, grid:{color:COLORS.grid} }
      }
    }
  };
}

// ── HISTORICAL TAB ────────────────────────────────────────────────────────────
function buildSC2MonthlyDeltas(country) {
  // Returns month-by-month SC2 delta (SC2 - Real) for 2025 and 2026 (full year)
  // If month not in sc2M → delta=0; if in sc2M and equal to real → delta≈0
  const ALL12 = [0,1,2,3,4,5,6,7,8,9,10,11];
  const deltas25 = ALL12.map(mi => {
    const md = (sc2M[2025]||{})[mi]||{};
    if (!(country in md)) return 0;
    const real = (((realM[2025]||{})[mi]||{})[country]||0);
    return md[country] - real;
  });
  const deltas26 = ALL12.map(mi => {
    const md = (sc2M[2026]||{})[mi]||{};
    if (!(country in md)) return 0;
    const real = (((realM[2026]||{})[mi]||{})[country]||0);
    return md[country] - real;
  });
  const tot25 = deltas25.reduce((s,v)=>s+v, 0);
  const tot26 = deltas26.reduce((s,v)=>s+v, 0);
  return {deltas25, deltas26, tot25, tot26};
}

function histLabels() { return [...YEARS_HIST.map(String), '2026 Real', 'BP 2026']; }

function histRealData(months, country) {
  const vals = YEARS_HIST.map(y => sumReal(y, months, country));
  vals.push(sumReal(2026, months, country));
  vals.push(null);
  return vals;
}
function histBPData(months, country) {
  const vals = YEARS_HIST.map(() => null);
  vals.push(null);
  vals.push(sumBP(months, country));
  return vals;
}
function histLatamRealData(months) {
  const vals = YEARS_HIST.map(y => sumLatam(y, months));
  vals.push(sumLatam(2026, months));
  vals.push(null);
  return vals;
}
function histLatamBPData(months) {
  return [...YEARS_HIST.map(()=>null), null, sumLatamBP(months)];
}
function histSC2Data(months, country) {
  const ptBg = YEARS_HIST.map(y => sc2HasAdjInSelected(country,y) ? '#f59e0b' : '#8b5cf6');
  ptBg.push(sc2HasAdjInSelected(country,2026) ? '#f59e0b' : '#8b5cf6');  // 2026 Real
  ptBg.push('#3b82f6');  // BP 2026 — fixed blue
  const vals = YEARS_HIST.map(y => sumSC2(y, months, country));
  vals.push(sumSC2(2026, months, country));    // 2026 Real SC2 (Real + adj)
  vals.push(sumSC2BP(months, country));         // BP 2026 SC2 (BP + adj)
  return {vals, ptBg};
}
function histLatamSC2Data(months) {
  const vals = YEARS_HIST.map(y => sumLatamSC2(y, months));
  vals.push(sumLatamSC2(2026, months));   // 2026 Real SC2
  vals.push(sumLatamSC2BP(months));        // BP 2026 SC2
  const ptBg = YEARS_HIST.map(y => SC2_COUNTRIES.some(c => sc2HasAdjInSelected(c,y)) ? '#f59e0b' : '#8b5cf6');
  ptBg.push(SC2_COUNTRIES.some(c => sc2HasAdjInSelected(c,2026)) ? '#f59e0b' : '#8b5cf6');
  ptBg.push('#3b82f6');  // BP 2026 — fixed blue
  return {vals, ptBg};
}

function renderHistorical() {
  const labels = histLabels();
  // LATAM total
  destroyChart('chHistLatam');
  const el = document.getElementById('chHistLatam');
  if (!el) return;
  el.style.height = '300px';
  charts.chHistLatam = new Chart(el, lineChartCfg(labels, [
    { label:'Real', data: histLatamRealData(selectedMonths), borderColor:'#f59e0b', backgroundColor:'rgba(245,158,11,.15)', fill:true, tension:.3, pointRadius:4, pointHoverRadius:6 },
    { label:'BP 2026', data: histLatamBPData(selectedMonths), borderColor:'#3b82f6', borderDash:[5,5], tension:.3, pointRadius:5, backgroundColor:'transparent' }
  ]));
  const kpiLatamEl = document.getElementById('histKpiLatam');
  if (kpiLatamEl) kpiLatamEl.innerHTML = histKpiHtml(sumLatam(2026,selectedMonths), sumLatam(2025,selectedMonths), sumLatamBP(selectedMonths));

  // Country lines
  const cGrid = document.getElementById('histCountryCharts');
  cGrid.innerHTML = '';
  const latamTot26 = sumLatam(2026, selectedMonths);
  COUNTRY_ORDER.forEach(c => {
    const cr26 = sumReal(2026, selectedMonths, c);
    const cr25 = sumReal(2025, selectedMonths, c);
    const cbp  = sumBP(selectedMonths, c);
    const share = latamTot26 > 0 ? (cr26/latamTot26*100).toFixed(1) : '0.0';
    const wrap = document.createElement('div');
    wrap.className = 'card';
    wrap.innerHTML = `<div class="section-title" id="histTitle_${c}">${flagImg(c)}${c} <span style="font-size:.75rem;color:var(--muted);font-weight:400">${share}% of LATAM</span></div><div class="chart-wrap" style="height:220px"><canvas id="chHist_${c}"></canvas></div><div id="histKpi_${c}">${histKpiHtml(cr26,cr25,cbp)}</div>`;
    cGrid.appendChild(wrap);
    const canvas = wrap.querySelector('canvas');
    const cid = 'chHist_' + c;
    destroyChart(cid);
    charts[cid] = new Chart(canvas, lineChartCfg(labels, [
      { label:'Real', data: histRealData(selectedMonths, c), borderColor: COUNTRY_COLORS[c], backgroundColor: COUNTRY_COLORS[c]+'22', fill:false, tension:.3, pointRadius:3 },
      { label:'BP 2026', data: histBPData(selectedMonths, c), borderColor:'#3b82f6', borderDash:[5,5], tension:.3, pointRadius:4, backgroundColor:'transparent' }
    ]));
  });

  // LATAM SC2
  const sc2res = histLatamSC2Data(selectedMonths);
  destroyChart('chHistLatamSC2');
  const el2 = document.getElementById('chHistLatamSC2');
  if (el2) {
    el2.style.height = '280px';
    charts.chHistLatamSC2 = new Chart(el2, lineChartCfg(labels, [
      { label:'Real', data: histLatamRealData(selectedMonths), borderColor:'#f59e0b', backgroundColor:'rgba(245,158,11,.1)', fill:false, tension:.3, pointRadius:4 },
      { label:'Scenario 2', data: sc2res.vals, borderColor:'#8b5cf6', backgroundColor:'rgba(139,92,246,.1)', fill:false, tension:.3, pointRadius:5, pointBackgroundColor: sc2res.ptBg },
      { label:'BP 2026', data: histLatamBPData(selectedMonths), borderColor:'#3b82f6', borderDash:[5,5], tension:.3, pointRadius:4, backgroundColor:'transparent' }
    ]));
  }

  // SC2 country charts
  const sc2Grid = document.getElementById('histSC2Charts');
  sc2Grid.innerHTML = '';
  SC2_COUNTRIES.forEach(c => {
    const {vals, ptBg} = histSC2Data(selectedMonths, c);
    const wrap = document.createElement('div');
    wrap.className = 'card';
    const effectName = SC2_EFFECTS[c];
    wrap.innerHTML = `
      <div class="section-title">${flagImg(c)}${c} — Scenario 2</div>
      <div style="font-size:.72rem;color:var(--muted);margin-bottom:6px">Effect: ${effectName}</div>
      <div class="chart-wrap" style="height:220px"><canvas id="chSC2_${c}"></canvas></div>
      <div class="sc2-legend"><span></span>Amber point = adjusted months in selection</div>
      <div class="sc2-detail" id="sc2Detail_${c}"></div>`;
    sc2Grid.appendChild(wrap);
    const cid = 'chSC2_' + c;
    destroyChart(cid);
    charts[cid] = new Chart(document.getElementById('chSC2_'+c), lineChartCfg(labels, [
      { label:'Real', data: histRealData(selectedMonths, c), borderColor: COUNTRY_COLORS[c], fill:false, tension:.3, pointRadius:3 },
      { label:'Scenario 2', data: vals, borderColor:'#8b5cf6', fill:false, tension:.3, pointRadius:5, pointBackgroundColor: ptBg },
      { label:'BP 2026', data: histBPData(selectedMonths, c), borderColor:'#3b82f6', borderDash:[5,5], tension:.3, pointRadius:4, backgroundColor:'transparent' }
    ]));
    renderSC2DetailTable(c);
  });
  tabDirty.historical = false;
}

function updateHistorical() {
  const labels = histLabels();
  // LATAM
  if (charts.chHistLatam) {
    charts.chHistLatam.data.datasets[0].data = histLatamRealData(selectedMonths);
    charts.chHistLatam.data.datasets[1].data = histLatamBPData(selectedMonths);
    charts.chHistLatam.update();
    const kpiLatamEl = document.getElementById('histKpiLatam');
    if (kpiLatamEl) kpiLatamEl.innerHTML = histKpiHtml(sumLatam(2026,selectedMonths), sumLatam(2025,selectedMonths), sumLatamBP(selectedMonths));
  }
  const latamTot26u = sumLatam(2026, selectedMonths);
  COUNTRY_ORDER.forEach(c => {
    const cid = 'chHist_' + c;
    if (charts[cid]) {
      charts[cid].data.datasets[0].data = histRealData(selectedMonths, c);
      charts[cid].data.datasets[1].data = histBPData(selectedMonths, c);
      charts[cid].update();
      const cr26u = sumReal(2026, selectedMonths, c);
      const share = latamTot26u > 0 ? (cr26u/latamTot26u*100).toFixed(1) : '0.0';
      const titleEl = document.getElementById('histTitle_' + c);
      if (titleEl) titleEl.innerHTML = `${flagImg(c)}${c} <span style="font-size:.75rem;color:var(--muted);font-weight:400">${share}% of LATAM</span>`;
      const kpiEl = document.getElementById('histKpi_' + c);
      if (kpiEl) kpiEl.innerHTML = histKpiHtml(cr26u, sumReal(2025,selectedMonths,c), sumBP(selectedMonths,c));
    }
  });
  if (charts.chHistLatamSC2) {
    const sc2res = histLatamSC2Data(selectedMonths);
    charts.chHistLatamSC2.data.datasets[0].data = histLatamRealData(selectedMonths);
    charts.chHistLatamSC2.data.datasets[1].data = sc2res.vals;
    charts.chHistLatamSC2.data.datasets[1].pointBackgroundColor = sc2res.ptBg;
    charts.chHistLatamSC2.data.datasets[2].data = histLatamBPData(selectedMonths);
    charts.chHistLatamSC2.update();
  }
  SC2_COUNTRIES.forEach(c => {
    const cid = 'chSC2_' + c;
    if (charts[cid]) {
      const {vals, ptBg} = histSC2Data(selectedMonths, c);
      charts[cid].data.datasets[0].data = histRealData(selectedMonths, c);
      charts[cid].data.datasets[1].data = vals;
      charts[cid].data.datasets[1].pointBackgroundColor = ptBg;
      charts[cid].data.datasets[2].data = histBPData(selectedMonths, c);
      charts[cid].update();
      renderSC2DetailTable(c);
    }
  });
}

function renderSC2DetailTable(country) {
  const el = document.getElementById('sc2Detail_' + country);
  if (!el) return;
  const rows = [];
  const allYears = [...YEARS_HIST, 2026];
  allYears.forEach(yr => {
    const diff = (sc2Diff[country]||{})[String(yr)]||[];
    const selDiff = diff.filter(mi => selectedMonths.includes(mi));
    if (selDiff.length === 0) return;
    const realTotal = selDiff.reduce((s,mi) => s + (((realM[yr]||{})[mi]||{})[country]||0), 0);
    const sc2Total  = selDiff.reduce((s,mi) => {
      const md = (sc2M[yr]||{})[mi]||{};
      return s + (country in md ? md[country] : (((realM[yr]||{})[mi]||{})[country]||0));
    }, 0);
    const delta = sc2Total - realTotal;
    rows.push(`<tr><td>${yr}</td><td style="text-align:right">${fmt(realTotal)}</td><td style="text-align:right">${fmt(sc2Total)}</td><td style="text-align:right;color:${delta>=0?'var(--green)':'var(--red)'}">${fmtSigned(Math.round(delta))}</td></tr>`);
  });
  if (rows.length === 0) { el.innerHTML = ''; return; }
  el.innerHTML = `<div style="margin-top:8px"><table><thead><tr><th style="width:20%;text-align:left">Year</th><th style="width:27%;text-align:right">Real</th><th style="width:27%;text-align:right">Scenario 2</th><th style="width:26%;text-align:right">Delta</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}

// ── ANNUAL TAB ────────────────────────────────────────────────────────────────
function annualData() {
  // 2018-2025 = Real; '2026 Real' = Real 2026; 'BP 2026' = BP full year
  const yearKeys = [...YEARS_HIST, '2026 Real', 'BP 2026'];
  const byCountry = {};
  COUNTRY_ORDER.forEach(c => {
    byCountry[c] = yearKeys.map(y => {
      if (y === '2026 Real') return sumReal(2026, selectedMonths, c);
      if (y === 'BP 2026')   return sumBP(selectedMonths, c);
      return sumReal(y, selectedMonths, c);
    });
  });
  const totals = yearKeys.map((_,i) => COUNTRY_ORDER.reduce((s,c) => s + byCountry[c][i], 0));
  return {yearKeys, byCountry, totals};
}

function renderAnnual() {
  const {yearKeys, byCountry, totals} = annualData();
  const labels = yearKeys.map(y => typeof y === 'number' ? String(y) : y);

  // Absolute stacked
  destroyChart('chAnnualAbs');
  const el1 = document.getElementById('chAnnualAbs');
  if (el1) {
    el1.style.height = '320px';
    const datasets = COUNTRY_ORDER.map(c => ({
      label: c, data: byCountry[c],
      backgroundColor: COUNTRY_COLORS[c] + 'cc',
      stack: 'a',
      datalabels: noLabelPlugin()
    }));
    // Phantom dataset for totals
    datasets.push({
      label:'_total', data: totals, backgroundColor:'transparent', stack:'a', type:'bar',
      datalabels: {
        display: true, anchor:'end', align:'top', font:{size:10},
        formatter: v => fmt(v),
        color: COLORS.text
      }
    });
    charts.chAnnualAbs = new Chart(el1, {
      type:'bar', data:{labels, datasets},
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{labels:{color:COLORS.text,font:{size:10}}, filter: i => i.text!=='_total' },
                  tooltip: mkTooltip(false) },
        scales:{
          x:{stacked:true, ticks:{color:COLORS.tick,font:{size:10}}, grid:{color:COLORS.grid}},
          y:{stacked:true, ticks:{color:COLORS.tick,font:{size:10},callback:v=>fmtK(v)}, grid:{color:COLORS.grid}}
        }
      }
    });
  }

  // Pct stacked
  destroyChart('chAnnualPct');
  const el2 = document.getElementById('chAnnualPct');
  if (el2) {
    el2.style.height = '320px';
    const pctDatasets = COUNTRY_ORDER.map(c => ({
      label: c,
      data: byCountry[c].map((v,i) => totals[i] > 0 ? +(v/totals[i]*100).toFixed(1) : 0),
      backgroundColor: COUNTRY_COLORS[c] + 'cc',
      stack: 'a',
      datalabels: noLabelPlugin()
    }));
    charts.chAnnualPct = new Chart(el2, {
      type:'bar', data:{labels, datasets: pctDatasets},
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{labels:{color:COLORS.text,font:{size:10}}}, tooltip: mkTooltip(true) },
        scales:{
          x:{stacked:true, ticks:{color:COLORS.tick,font:{size:10}}, grid:{color:COLORS.grid}},
          y:{stacked:true, max:100, ticks:{color:COLORS.tick,font:{size:10},callback:v=>v+'%'}, grid:{color:COLORS.grid}}
        }
      }
    });
  }

  // Table
  const tbl = document.getElementById('annualTable');
  if (tbl) tbl.innerHTML = buildAnnualTable(yearKeys, byCountry, totals);
  tabDirty.annual = false;
}

function buildAnnualTable(yearKeys, byCountry, totals) {
  const hdrs = yearKeys.map(y => typeof y === 'number' ? String(y) : y);
  const colW = Math.floor(78/hdrs.length);
  let h = `<table><thead><tr><th style="width:22%">Country</th>${hdrs.map(h=>`<th style="width:${colW}%">${h}</th>`).join('')}</tr></thead><tbody>`;
  COUNTRY_ORDER.forEach(c => {
    h += `<tr><td>${flagImg(c)}${c}</td>${byCountry[c].map(v=>`<td>${fmt(v)}</td>`).join('')}</tr>`;
  });
  h += `<tr class="total-row"><td>LATAM TOTAL</td>${totals.map(v=>`<td>${fmt(v)}</td>`).join('')}</tr>`;
  h += '</tbody></table>';
  return h;
}

function updateAnnual() {
  const {yearKeys, byCountry, totals} = annualData();
  const labels = yearKeys.map(y => typeof y === 'number' ? String(y) : y);
  if (charts.chAnnualAbs) {
    charts.chAnnualAbs.data.labels = labels;
    COUNTRY_ORDER.forEach((c,i) => { charts.chAnnualAbs.data.datasets[i].data = byCountry[c]; });
    charts.chAnnualAbs.data.datasets[COUNTRY_ORDER.length].data = totals;
    charts.chAnnualAbs.update();
  }
  if (charts.chAnnualPct) {
    charts.chAnnualPct.data.labels = labels;
    COUNTRY_ORDER.forEach((c,i) => {
      charts.chAnnualPct.data.datasets[i].data = byCountry[c].map((v,j) => totals[j]>0?+(v/totals[j]*100).toFixed(1):0);
    });
    charts.chAnnualPct.update();
  }
  const tbl = document.getElementById('annualTable');
  if (tbl) tbl.innerHTML = buildAnnualTable(yearKeys, byCountry, totals);
}

// ── PERIOD COMPARISON TAB ─────────────────────────────────────────────────────
function renderPeriod() {
  const periods = ['2024','2025','2026 Real','BP 2026'];
  const periodColors = ['#94a3b8','#3b82f6','#f59e0b','#10b981'];

  // Grouped bar by country
  destroyChart('chPeriodGrouped');
  const el = document.getElementById('chPeriodGrouped');
  if (el) {
    el.style.height = '320px';
    const datasets = periods.map((p,pi) => ({
      label: p,
      data: COUNTRY_ORDER.map(c => {
        if (p==='BP 2026') return sumBP(selectedMonths, c);
        const yr = p==='2026 Real'?2026:parseInt(p);
        return sumReal(yr, selectedMonths, c);
      }),
      backgroundColor: periodColors[pi] + 'cc',
      datalabels: noLabelPlugin()
    }));
    charts.chPeriodGrouped = new Chart(el, {
      type:'bar', data:{labels: COUNTRY_LABELS, datasets},
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{labels:{color:COLORS.text,font:{size:10}}}, tooltip: mkTooltip(false) },
        scales:{
          x:{ticks:{color:COLORS.tick,font:{size:10}}, grid:{color:COLORS.grid}},
          y:{ticks:{color:COLORS.tick,font:{size:10},callback:v=>fmtK(v)}, grid:{color:COLORS.grid}}
        }
      }
    });
  }

  // Waterfall LATAM: 2025 base → change to 2026 Real → change to BP
  destroyChart('chWaterfall');
  const el2 = document.getElementById('chWaterfall');
  if (el2) {
    el2.style.height = '320px';
    const v25  = sumLatam(2025, selectedMonths);
    const v26  = sumLatam(2026, selectedMonths);
    const vbp  = sumLatamBP(selectedMonths);
    const d26  = v26 - v25;
    const dbp  = vbp - v26;
    const wfLabels = ['2025 Base','▲ to 2026 Real','2026 Real','▲ to BP','BP 2026'];
    const wfBase   = [0, v25, 0, v26, 0];
    const wfVals   = [v25, Math.abs(d26), v26, Math.abs(dbp), vbp];
    const wfSigned = [v25, d26, v26, dbp, vbp];
    const wfColors = ['#3b82f6', d26>=0?'#10b981':'#ef4444', '#f59e0b', dbp>=0?'#10b981':'#ef4444', '#8b5cf6'];
    charts.chWaterfall = new Chart(el2, {
      type:'bar',
      data:{
        labels: wfLabels,
        datasets:[
          { label:'Base', data: wfBase, backgroundColor:'transparent', stack:'w', datalabels:{display:false} },
          { label:'Value', data: wfVals, backgroundColor: wfColors, stack:'w',
            datalabels:{display:true, anchor:'end', align:'top', font:{size:10},
              formatter:(v,ctx) => {
                const s = wfSigned[ctx.dataIndex];
                const lbl = wfLabels[ctx.dataIndex];
                if (lbl.startsWith('▲')) return fmtSigned(s);
                return fmt(s);
              },
              color:(ctx)=>{
                const lbl = wfLabels[ctx.dataIndex];
                if (lbl.startsWith('▲')) return wfSigned[ctx.dataIndex]>=0?'#10b981':'#ef4444';
                return COLORS.text;
              }
            }
          }
        ]
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{display:false}, tooltip:{callbacks:stdTooltipCbk} },
        scales:{
          x:{ticks:{color:COLORS.tick,font:{size:10}}, grid:{color:COLORS.grid}},
          y:{ticks:{color:COLORS.tick,font:{size:10},callback:v=>fmtK(v)}, grid:{color:COLORS.grid}}
        }
      }
    });
  }
  tabDirty.period = false;
}

function updatePeriod() {
  if (charts.chPeriodGrouped) {
    charts.chPeriodGrouped.data.labels = COUNTRY_LABELS;
    const periods = ['2024','2025','2026 Real','BP 2026'];
    periods.forEach((p,pi) => {
      charts.chPeriodGrouped.data.datasets[pi].data = COUNTRY_ORDER.map(c => {
        if (p==='BP 2026') return sumBP(selectedMonths, c);
        const yr = p==='2026 Real'?2026:parseInt(p);
        return sumReal(yr, selectedMonths, c);
      });
    });
    charts.chPeriodGrouped.update();
  }
  if (charts.chWaterfall) {
    const v25 = sumLatam(2025, selectedMonths);
    const v26 = sumLatam(2026, selectedMonths);
    const vbp = sumLatamBP(selectedMonths);
    const d26 = v26 - v25, dbp = vbp - v26;
    const wfSigned = [v25, d26, v26, dbp, vbp];
    const wfLabels = ['2025 Base','▲ to 2026 Real','2026 Real','▲ to BP','BP 2026'];
    charts.chWaterfall.data.datasets[0].data = [0, v25, 0, v26, 0];
    charts.chWaterfall.data.datasets[1].data = [v25, Math.abs(d26), v26, Math.abs(dbp), vbp];
    charts.chWaterfall.data.datasets[1].backgroundColor = ['#3b82f6', d26>=0?'#10b981':'#ef4444', '#f59e0b', dbp>=0?'#10b981':'#ef4444','#8b5cf6'];
    charts.chWaterfall.data.datasets[1].datalabels = {
      display:true, anchor:'end', align:'top', font:{size:10},
      formatter:(v,ctx) => {
        const s = wfSigned[ctx.dataIndex];
        const lbl = wfLabels[ctx.dataIndex];
        if (lbl.startsWith('▲')) return fmtSigned(s);
        return fmt(s);
      },
      color:(ctx)=>{
        const lbl = wfLabels[ctx.dataIndex];
        if (lbl.startsWith('▲')) return wfSigned[ctx.dataIndex]>=0?'#10b981':'#ef4444';
        return COLORS.text;
      }
    };
    charts.chWaterfall.update();
  }
}

// ── COUNTRY ANALYSIS TAB ──────────────────────────────────────────────────────

// Per-country data helpers
function sumCuC(country, year, months, cust) {
  const cd = (cuCReal[country] || {})[year] || {};
  return months.reduce((s,mi) => s + ((cd[mi]||{})[cust]||0), 0);
}
function sumCuCBP(country, months, cust) {
  const cd = cuCBP[country] || {};
  return months.reduce((s,mi) => s + ((cd[mi]||{})[cust]||0), 0);
}
function sumB4C(year, months, country, brand) {
  const yd = b4CReal[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[country])||{})[brand]||0), 0);
}
function sumB4CBP(months, country, brand) {
  return months.reduce((s,mi) => s + ((((b4CBP[mi]||{})[country])||{})[brand]||0), 0);
}
function sumChanC(country, year, months, channel) {
  const yd = chCReal[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[country])||{})[channel]||0), 0);
}
function sumChanCBP(country, months, channel) {
  return months.reduce((s,mi) => s + ((((chCBP[mi]||{})[country])||{})[channel]||0), 0);
}
function sumFamC(country, year, months, fam) {
  const yd = famCReal[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[country])||{})[fam]||0), 0);
}
function sumFamCBP(country, months, fam) {
  return months.reduce((s,mi) => s + ((((famCBP[mi]||{})[country])||{})[fam]||0), 0);
}
function sumB2C(country, year, months, brand) {
  const yd = b2CReal[year] || {};
  return months.reduce((s,mi) => s + ((((yd[mi]||{})[country])||{})[brand]||0), 0);
}
function sumB2CBP(country, months, brand) {
  return months.reduce((s,mi) => s + ((((b2CBP[mi]||{})[country])||{})[brand]||0), 0);
}
function sumSkuC(country, year, months, sku) {
  const yd = (skuCReal[country]||{})[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[sku]||0), 0);
}

function renderCountryTab() {
  const pillBar = document.getElementById('countryPillBar');
  if (!pillBar.hasChildNodes()) {
    COUNTRY_ORDER.forEach(c => {
      const btn = document.createElement('button');
      btn.className = 'cpill' + (c === currentCountry ? ' active' : '');
      btn.innerHTML = flagImg(c) + c;
      btn.onclick = () => {
        currentCountry = c;
        document.querySelectorAll('.cpill').forEach(el => el.classList.remove('active'));
        btn.classList.add('active');
        renderCountryContent();
      };
      pillBar.appendChild(btn);
    });
  }
  renderCountryContent();
  tabDirty.country = false;
}

function renderCountryContent() {
  const c = currentCountry;
  if (currentSubTab === 'channels')  renderCChannels(c);
  else if (currentSubTab === 'customers') renderCCustomers(c);
  else if (currentSubTab === 'salescust') renderCSalesByCu(c);
  else if (currentSubTab === 'custbrand') renderCCustBrand(c);
  else if (currentSubTab === 'brands')    renderCBrands(c);
  else if (currentSubTab === 'family')    renderCFamily(c);
  else if (currentSubTab === 'products')  renderCProducts(c);
}

let salesCuRowsC=[], salesCuTotalsC={T24:0,TQ24:0,T25:0,TQ25:0,T26:0,TQ26:0};
function renderCSalesByCu(country) {
  const cc = document.getElementById('countryContent');
  const cuList  = (allCuCList[country]  || []);
  const cuData  =  allCuCReal[country]  || {};
  const cuDataQ =  allCuCRealQ[country] || {};
  const cuChMap =  allCuCChannelMap[country] || {};
  function sumC(yr,months,cu){ return months.reduce((s,mi)=>s+(((cuData[yr]||{})[mi]||{})[cu]||0),0); }
  function sumCQ(yr,months,cu){ return months.reduce((s,mi)=>s+(((cuDataQ[yr]||{})[mi]||{})[cu]||0),0); }
  const rows = cuList.map(cu=>({
    cu, ch:cuChMap[cu]||'—',
    v24:sumC(2024,selectedMonths,cu), q24:sumCQ(2024,selectedMonths,cu),
    v25:sumC(2025,selectedMonths,cu), q25:sumCQ(2025,selectedMonths,cu),
    v26:sumC(2026,selectedMonths,cu), q26:sumCQ(2026,selectedMonths,cu)
  })).filter(r=>r.v24||r.v25||r.v26).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
  salesCuRowsC=rows;
  salesCuTotalsC={
    T24:rows.reduce((s,r)=>s+r.v24,0), TQ24:rows.reduce((s,r)=>s+r.q24,0),
    T25:rows.reduce((s,r)=>s+r.v25,0), TQ25:rows.reduce((s,r)=>s+r.q25,0),
    T26:rows.reduce((s,r)=>s+r.v26,0), TQ26:rows.reduce((s,r)=>s+r.q26,0)
  };
  const channels=[...new Set(rows.map(r=>r.ch).filter(c=>c&&c!=='—'))].sort();
  const chOpts=channels.map(c=>`<option value="${c}">${c}</option>`).join('');
  const inputStyle='background:var(--card);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:5px 10px;font-size:.78rem';
  cc.innerHTML = `<div class="card"><div class="section-title">${flagImg(country)}${country} — Sales by Customer</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
      <input type="text" id="salesCuSearchC" placeholder="Search customer..." oninput="renderCSalesByCuTable()" style="${inputStyle};min-width:220px">
      <select id="salesCuChannelC" onchange="renderCSalesByCuTable()" style="${inputStyle}">
        <option value="">All Channels</option>${chOpts}
      </select>
      <span id="salesCuCountC" style="font-size:.72rem;color:var(--muted);margin-left:auto"></span>
    </div>
    <div class="tbl-wrap" id="salesCustTblC_${country}"></div></div>`;
  renderCSalesByCuTable();
}
function renderCSalesByCuTable() {
  const tbl = document.getElementById('salesCustTblC_' + currentCountry);
  if (!tbl) return;
  const searchEl=document.getElementById('salesCuSearchC'), chEl=document.getElementById('salesCuChannelC');
  const search=(searchEl?searchEl.value:'').trim().toLowerCase();
  const chFilter=chEl?chEl.value:'';
  const rows=salesCuRowsC.filter(r=>(!search||r.cu.toLowerCase().includes(search))&&(!chFilter||r.ch===chFilter));
  const {T24,TQ24,T25,TQ25,T26,TQ26}=salesCuTotalsC;
  const tref25=viewMode==='qty'?TQ25||1:T25||1, tref26=viewMode==='qty'?TQ26||1:T26||1;
  const HDR=`<tr><th style="width:19%;text-align:left">Customer</th><th style="width:9%">Channel</th><th style="width:9%">2024</th><th style="width:9%">2025</th><th style="width:9%">vs 2024</th><th style="width:9%">2026 Real</th><th style="width:9%">vs 2025</th><th style="width:9%">Share '25</th><th style="width:9%">Share '26</th></tr>`;
  const dT24=getV(T24,TQ24), dT25=getV(T25,TQ25), dT26=getV(T26,TQ26);
  let h=`<table style="table-layout:fixed"><thead>${HDR}</thead><tbody>`;
  h+=`<tr class="total-row"><td>TOTAL</td><td></td><td>${fmtV(T24,TQ24)}</td><td>${fmtV(T25,TQ25)}</td><td>${pctPillSafe(dT25,dT24)}</td><td>${fmtV(T26,TQ26)}</td><td>${pctPillSafe(dT26,dT25,dT24)}</td><td>100%</td><td>100%</td></tr>`;
  if(rows.length===0){
    h+=`<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:14px">No customers match the filters</td></tr>`;
  }
  rows.forEach(({cu,ch,v24,q24,v25,q25,v26,q26})=>{
    const d24=getV(v24,q24), d25=getV(v25,q25), d26=getV(v26,q26);
    const sh25=tref25>0?(d25/tref25*100).toFixed(1)+'%':'—';
    const sh26=tref26>0?(d26/tref26*100).toFixed(1)+'%':'—';
    h+=`<tr><td style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.78rem" title="${cu}">${cu}</td>`;
    h+=`<td style="font-size:.68rem;color:var(--muted)">${ch}</td>`;
    h+=`<td>${fmtV(v24,q24)}</td><td>${fmtV(v25,q25)}</td><td>${pctPillSafe(d25,d24)}</td>`;
    h+=`<td>${fmtV(v26,q26)}</td><td>${pctPillSafe(d26,d25,d24)}</td>`;
    h+=`<td>${sh25}</td><td>${sh26}</td></tr>`;
  });
  h+='</tbody></table>';
  tbl.innerHTML = h;
  const cnt=document.getElementById('salesCuCountC');
  if(cnt) cnt.textContent=`Showing ${rows.length} of ${salesCuRowsC.length} customers`;
}

function renderCChannels(country) {
  const cc = document.getElementById('countryContent');
  const cid = 'chCC_' + country;
  cc.innerHTML = `
    <div class="row2 mb16">
      <div class="card">
        <div class="section-title">${flagImg(country)}${country} — Channels</div>
        <div class="chart-wrap" style="height:280px"><canvas id="${cid}"></canvas></div>
      </div>
      <div class="card">
        <div class="tbl-wrap" id="chanTblC_${country}"></div>
      </div>
    </div>`;
  destroyChart(cid);
  const el = document.getElementById(cid);
  if (el) {
    const chData = CHANNELS.map(ch => ({
      ch,
      v26:sumChanC(country,2026,selectedMonths,ch), q26:sumChanCQ(country,2026,selectedMonths,ch),
      v25:sumChanC(country,2025,selectedMonths,ch), q25:sumChanCQ(country,2025,selectedMonths,ch),
      vBP:sumChanCBP(country,selectedMonths,ch),   qBP:sumChanCBPQ(country,selectedMonths,ch)
    })).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
    const labels=chData.map(x=>x.ch);
    const vals26=chData.map(x=>getV(x.v26,x.q26));
    const vals25=chData.map(x=>getV(x.v25,x.q25));
    const valsBP=chData.map(x=>getV(x.vBP,x.qBP));
    charts[cid] = new Chart(el, {
      type:'bar',
      data:{ labels, datasets:[
        {label:'2026 Real', data:vals26, backgroundColor:'#f59e0b99',
          datalabels:{display:true,anchor:'end',align:'top',font:{size:10},formatter:v=>fmtChartLbl(v),color:COLORS.text}},
        {label:'2025', data:vals25, backgroundColor:'#3b82f699', datalabels:noLabelPlugin()},
        {label:'BP 2026', data:valsBP, backgroundColor:'#10b98199', datalabels:noLabelPlugin()}
      ]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:COLORS.text,font:{size:10}}},
                 tooltip:{mode:'index',intersect:false,callbacks:{label:ctx=>' '+ctx.dataset.label+': '+fmtChartTooltip(ctx.raw)}}},
        scales:{x:{ticks:{color:COLORS.tick,font:{size:10}},grid:{color:COLORS.grid}},
                y:{ticks:{color:COLORS.tick,font:{size:10},callback:v=>fmtChartLbl(v)},grid:{color:COLORS.grid}}}}
    });
  }
  const tbl = document.getElementById('chanTblC_' + country);
  if (tbl) {
    const chRows = CHANNELS.map(ch => ({
      ch,
      v25:sumChanC(country,2025,selectedMonths,ch), q25:sumChanCQ(country,2025,selectedMonths,ch),
      v26:sumChanC(country,2026,selectedMonths,ch), q26:sumChanCQ(country,2026,selectedMonths,ch),
      vBP:sumChanCBP(country,selectedMonths,ch),   qBP:sumChanCBPQ(country,selectedMonths,ch)
    })).filter(x=>x.v25||x.v26||x.vBP).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
    const tot25=chRows.reduce((s,x)=>s+x.v25,0)||1;
    const tot26=chRows.reduce((s,x)=>s+x.v26,0)||1;
    const totQ25=chRows.reduce((s,x)=>s+x.q25,0)||1;
    const totQ26=chRows.reduce((s,x)=>s+x.q26,0)||1;
    let h=`<table><thead><tr><th style="width:20%">Channel</th><th style="width:12%">2025</th><th style="width:13%">2026 Real</th><th style="width:10%">vs 2025</th><th style="width:12%">BP 2026</th><th style="width:10%">vs BP</th><th style="width:11%">Share '25</th><th style="width:12%">Share '26</th></tr></thead><tbody>`;
    let t25=0,tQ25=0,t26=0,tQ26=0,tbp=0,tBPQ=0;
    chRows.forEach(({ch,v25,q25,v26,q26,vBP,qBP})=>{
      t25+=v25;tQ25+=q25;t26+=v26;tQ26+=q26;tbp+=vBP;tBPQ+=qBP;
      const d25=getV(v25,q25),d26=getV(v26,q26),dBP=getV(vBP,qBP);
      const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
      h+=`<tr><td>${ch}</td><td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>`;
      h+=`<td>${pctPillSafe(d26,d25)}</td><td>${fmtV(vBP,qBP)}</td><td>${pctPillSafeBP(d26,dBP)}</td>`;
      h+=`<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td><td>${tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
    });
    const td25=getV(t25,tQ25),td26=getV(t26,tQ26),tdbp=getV(tbp,tBPQ);
    h+=`<tr class="total-row"><td>TOTAL</td><td>${fmtV(t25,tQ25)}</td><td>${fmtV(t26,tQ26)}</td><td>${pctPillSafe(td26,td25)}</td><td>${fmtV(tbp,tBPQ)}</td><td>${pctPillSafeBP(td26,tdbp)}</td><td>100%</td><td>100%</td></tr>`;
    tbl.innerHTML = h + '</tbody></table>';
  }
}

function renderCCustBrand(country) {
  const cc = document.getElementById('countryContent');
  cc.innerHTML = `<div class="card"><div class="section-title">${flagImg(country)}${country} — Customer × Brand × Category</div><div class="tbl-wrap" id="cbMtx_${country}"></div></div>`;
  const tbl = document.getElementById('cbMtx_' + country);
  if (!tbl) return;
  const allCus = cbTops[country] || [];
  const cuRows = allCus.map(cu => {
    const v25=sumCuTotalCb(country,2025,selectedMonths,cu);
    const q25=sumCuTotalCbQ(country,2025,selectedMonths,cu);
    const v26=sumCuTotalCb(country,2026,selectedMonths,cu);
    const q26=sumCuTotalCbQ(country,2026,selectedMonths,cu);
    return {cu,v25,q25,v26,q26};
  }).filter(x=>x.v25>0||x.v26>0).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26)).slice(0,5);
  if (!cuRows.length) { tbl.innerHTML='<p style="color:var(--muted);padding:20px">No data.</p>'; return; }
  const ctryV25=sumReal(2025,selectedMonths,country)||1;
  const ctryV26=sumReal(2026,selectedMonths,country)||1;
  const ctryQ25=sumRealQ(2025,selectedMonths,country)||1;
  const ctryQ26=sumRealQ(2026,selectedMonths,country)||1;
  const HDR=`<tr><th style="width:36%;text-align:left">Customer / Brand / Category</th><th style="width:12%">2025</th><th style="width:13%">2026 Real</th><th style="width:10%">vs 2025</th><th style="width:14%">Share '25</th><th style="width:15%">Share '26</th></tr>`;
  let h=`<table><thead>${HDR}</thead><tbody>`;
  cuRows.forEach(({cu,v25,q25,v26,q26})=>{
    const d25=getV(v25,q25),d26=getV(v26,q26);
    const ref25=getV(ctryV25,ctryQ25)||1, ref26=getV(ctryV26,ctryQ26)||1;
    h+=`<tr style="background:rgba(245,158,11,.08)"><td style="font-weight:700;font-size:.74rem;padding:5px 7px">${cu}</td><td style="font-weight:600">${fmtV(v25,q25)}</td><td style="font-weight:600">${fmtV(v26,q26)}</td><td>${pctPillTight(d26,d25)}</td><td style="font-weight:600">${ref25>0?(d25/ref25*100).toFixed(1)+'%':'—'}</td><td style="font-weight:600">${ref26>0?(d26/ref26*100).toFixed(1)+'%':'—'}</td></tr>`;
    const brands=getBrandsForCu(country,cu);
    const brandRows=brands.map(b=>({b,v25:sumCbC(country,2025,selectedMonths,cu,b),q25:sumCbCQ(country,2025,selectedMonths,cu,b),v26:sumCbC(country,2026,selectedMonths,cu,b),q26:sumCbCQ(country,2026,selectedMonths,cu,b)}))
      .filter(x=>x.v25>0||x.v26>0).sort((a,b2)=>getV(b2.v26,b2.q26)-getV(a.v26,a.q26));
    const cuRef25=d25||1, cuRef26=d26||1;
    brandRows.forEach(({b,v25:bv25,q25:bq25,v26:bv26,q26:bq26})=>{
      const bd25=getV(bv25,bq25),bd26=getV(bv26,bq26);
      h+=`<tr><td style="padding-left:22px;font-size:.72rem"><span style="color:var(--muted);margin-right:4px">▸</span>${b}</td><td>${fmtV(bv25,bq25)}</td><td>${fmtV(bv26,bq26)}</td><td>${pctPillTight(bd26,bd25)}</td><td>${cuRef25>0?(bd25/cuRef25*100).toFixed(1)+'%':'—'}</td><td>${cuRef26>0?(bd26/cuRef26*100).toFixed(1)+'%':'—'}</td></tr>`;
      if (b==='TRAVEL BLUE') {
        const fams=getFamsForCuTB(country,cu);
        const famRows=fams.map(fam=>({fam,v25:sumCbcTBFam(country,2025,selectedMonths,cu,fam),q25:sumCbcTBFamQ(country,2025,selectedMonths,cu,fam),v26:sumCbcTBFam(country,2026,selectedMonths,cu,fam),q26:sumCbcTBFamQ(country,2026,selectedMonths,cu,fam)}))
          .filter(x=>x.v25>0||x.v26>0).sort((a,c2)=>getV(c2.v26,c2.q26)-getV(a.v26,a.q26));
        const tbRef25=bd25||1, tbRef26=bd26||1;
        famRows.forEach(({fam,v25:fv25,q25:fq25,v26:fv26,q26:fq26})=>{
          const fd25=getV(fv25,fq25),fd26=getV(fv26,fq26);
          h+=`<tr style="background:rgba(16,185,129,.05)"><td style="padding-left:42px;font-size:.7rem;color:#6ee7b7"><span style="margin-right:4px">◆</span>${fam}</td><td>${fmtV(fv25,fq25)}</td><td>${fmtV(fv26,fq26)}</td><td>${pctPillTight(fd26,fd25)}</td><td>${tbRef25>0?(fd25/tbRef25*100).toFixed(1)+'%':'—'}</td><td>${tbRef26>0?(fd26/tbRef26*100).toFixed(1)+'%':'—'}</td></tr>`;
          const famCats=getCatsForFam(country,cu,fam);
          const catRows=famCats.map(cat=>({cat,v25:sumCbcTBFamCat(country,2025,selectedMonths,cu,fam,cat),q25:sumCbcTBFamCatQ(country,2025,selectedMonths,cu,fam,cat),v26:sumCbcTBFamCat(country,2026,selectedMonths,cu,fam,cat),q26:sumCbcTBFamCatQ(country,2026,selectedMonths,cu,fam,cat)}))
            .filter(x=>x.v25>0||x.v26>0).sort((a,c2)=>getV(c2.v26,c2.q26)-getV(a.v26,a.q26));
          catRows.forEach(({cat,v25:cv25,q25:cq25,v26:cv26,q26:cq26})=>{
            const cd25=getV(cv25,cq25),cd26=getV(cv26,cq26);
            h+=`<tr style="background:rgba(59,130,246,.04)"><td style="padding-left:62px;font-size:.68rem;color:var(--muted)"><span style="margin-right:4px">•</span>${cat}</td><td>${fmtV(cv25,cq25)}</td><td>${fmtV(cv26,cq26)}</td><td>${pctPillTight(cd26,cd25)}</td><td>${fd25>0?(cd25/fd25*100).toFixed(1)+'%':'—'}</td><td>${fd26>0?(cd26/fd26*100).toFixed(1)+'%':'—'}</td></tr>`;
          });
        });
      }
    });
  });
  h+='</tbody></table>';
  tbl.innerHTML=h;
}

function buildBccMatrix(country) {
  const bcTops = bccTops[country] || {};
  const bcKeys = Object.keys(bcTops);
  if (!bcKeys.length) return '';
  const bcData = bcKeys.map(bc => {
    const tops = bcTops[bc];
    const v26=tops.reduce((s,cu)=>s+sumBccC(country,2026,selectedMonths,bc,cu),0);
    const v25=tops.reduce((s,cu)=>s+sumBccC(country,2025,selectedMonths,bc,cu),0);
    const q26=tops.reduce((s,cu)=>s+sumBccCQ(country,2026,selectedMonths,bc,cu),0);
    const q25=tops.reduce((s,cu)=>s+sumBccCQ(country,2025,selectedMonths,bc,cu),0);
    return {bc,tops,v26,v25,q26,q25};
  }).filter(x=>x.v26>0||x.v25>0).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
  if (!bcData.length) return '';
  let html=`<div class="card mt12"><div class="section-title"><i class="bi bi-grid-3x3-gap-fill"></i> Top 5 Customers by Brand × Category</div><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:12px;margin-top:10px">`;
  bcData.forEach(({bc,tops})=>{
    const [brand,cat]=bc.split('|||');
    const rows=tops.map(cu=>({
      cu,
      v25:sumBccC(country,2025,selectedMonths,bc,cu), q25:sumBccCQ(country,2025,selectedMonths,bc,cu),
      v26:sumBccC(country,2026,selectedMonths,bc,cu), q26:sumBccCQ(country,2026,selectedMonths,bc,cu)
    })).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26)).slice(0,5)
      .filter(r=>r.v25>0||r.v26>0);
    if(!rows.length) return;
    const tot25=rows.reduce((s,r)=>s+getV(r.v25,r.q25),0)||1;
    const tot26=rows.reduce((s,r)=>s+getV(r.v26,r.q26),0)||1;
    html+=`<div><div style="font-size:.75rem;font-weight:700;color:var(--accent);margin-bottom:4px;padding:3px 8px;background:rgba(245,158,11,.08);border-left:3px solid var(--accent);border-radius:2px">${brand} — ${cat}</div>`;
    html+=`<table style="width:100%;font-size:.7rem;border-collapse:collapse"><thead><tr style="background:var(--tbl-head)"><th style="width:32%;text-align:left;padding:4px 5px;color:#fff">Customer</th><th style="width:13%;text-align:right;padding:4px 5px;color:#fff">2025</th><th style="width:14%;text-align:right;padding:4px 5px;color:#fff">2026 Real</th><th style="width:11%;text-align:right;padding:4px 5px;color:#fff">vs 2025</th><th style="width:15%;text-align:right;padding:4px 5px;color:#fff">Share '25</th><th style="width:15%;text-align:right;padding:4px 5px;color:#fff">Share '26</th></tr></thead><tbody>`;
    rows.forEach(({cu,v25,q25,v26,q26})=>{
      const d25=getV(v25,q25),d26=getV(v26,q26);
      html+=`<tr style="border-bottom:1px solid var(--border)"><td style="padding:3px 5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${cu}">${cu}</td><td style="padding:3px 5px;text-align:right">${fmtV(v25,q25)}</td><td style="padding:3px 5px;text-align:right">${fmtV(v26,q26)}</td><td style="padding:3px 5px;text-align:right">${pctPillSafe(d26,d25)}</td><td style="padding:3px 5px;text-align:right">${tot25>0?(d25/tot25*100).toFixed(1)+'%':'—'}</td><td style="padding:3px 5px;text-align:right">${tot26>0?(d26/tot26*100).toFixed(1)+'%':'—'}</td></tr>`;
    });
    html+='</tbody></table></div>';
  });
  html+='</div></div>';
  return html;
}

const SMALL_CTRY = new Set(['ARGENTINA','COLOMBIA','CHILE','PANAMA','PERU']);
function sumSmallCuC(country,year,months,cu){const cd=(smallCuCReal[country]||{})[year]||{};return months.reduce((s,mi)=>s+((cd[mi]||{})[cu]||0),0);}
function sumSmallCuCBP(country,months,cu){const cd=smallCuCBP[country]||{};return months.reduce((s,mi)=>s+((cd[mi]||{})[cu]||0),0);}
function sumSmallCuCQ(country,year,months,cu){const cd=(smallCuCRealQ[country]||{})[year]||{};return months.reduce((s,mi)=>s+((cd[mi]||{})[cu]||0),0);}
function sumSmallCuCBPQ(country,months,cu){const cd=smallCuCBPQ[country]||{};return months.reduce((s,mi)=>s+((cd[mi]||{})[cu]||0),0);}

function renderSmallCCustomers(country) {
  const cc = document.getElementById('countryContent');
  cc.innerHTML = `<div class="card mb16"><div class="section-title">${flagImg(country)}${country} — Customers</div><div class="tbl-wrap" id="custTblC_${country}"></div></div><div id="bccMtx_${country}"></div>`;
  const tbl = document.getElementById('custTblC_' + country);
  if (!tbl) return;
  const tops = smallCuTops[country] || [];
  const tot25=sumReal(2025,selectedMonths,country)||1, tot26=sumReal(2026,selectedMonths,country)||1;
  const totQ25=sumRealQ(2025,selectedMonths,country)||1, totQ26=sumRealQ(2026,selectedMonths,country)||1;
  const rows = tops.map(cu=>({
    cu, channel:smallCuChannelMap[cu]||'—',
    v24:sumSmallCuC(country,2024,selectedMonths,cu), q24:sumSmallCuCQ(country,2024,selectedMonths,cu),
    v25:sumSmallCuC(country,2025,selectedMonths,cu), q25:sumSmallCuCQ(country,2025,selectedMonths,cu),
    v26:sumSmallCuC(country,2026,selectedMonths,cu), q26:sumSmallCuCQ(country,2026,selectedMonths,cu),
    vBP:sumSmallCuCBP(country,selectedMonths,cu),   qBP:sumSmallCuCBPQ(country,selectedMonths,cu)
  })).filter(x=>x.v25||x.v26||x.vBP).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
  let h=`<table><thead><tr><th style="width:20%">Customer</th><th style="width:9%">Channel</th><th style="width:11%">2025</th><th style="width:11%">2026 Real</th><th style="width:9%">vs 2025</th><th style="width:11%">BP 2026</th><th style="width:9%">vs BP</th><th style="width:10%">Share '25</th><th style="width:10%">Share '26</th></tr></thead><tbody>`;
  let t25=0,tQ25=0,t26=0,tQ26=0,tbp=0,tBPQ=0;
  rows.forEach(({cu,channel,v24,q24,v25,q25,v26,q26,vBP,qBP})=>{
    t25+=v25;tQ25+=q25;t26+=v26;tQ26+=q26;tbp+=vBP;tBPQ+=qBP;
    const d24=getV(v24,q24),d25=getV(v25,q25),d26=getV(v26,q26),dBP=getV(vBP,qBP);
    const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
    h+=`<tr><td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${cu}">${cu}</td>`;
    h+=`<td style="font-size:.68rem;color:var(--muted)">${channel}</td>`;
    h+=`<td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>`;
    h+=`<td>${pctPillSafe(d26,d25,d24)}</td><td>${fmtV(vBP,qBP)}</td><td>${pctPillSafeBP(d26,dBP)}</td>`;
    h+=`<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td><td>${tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
  });
  const td25=getV(t25,tQ25),td26=getV(t26,tQ26),tdbp=getV(tbp,tBPQ);
  h+=`<tr class="total-row"><td>TOTAL</td><td></td><td>${fmtV(t25,tQ25)}</td><td>${fmtV(t26,tQ26)}</td><td>${pctPillSafe(td26,td25)}</td><td>${fmtV(tbp,tBPQ)}</td><td>${pctPillSafeBP(td26,tdbp)}</td><td>100%</td><td>100%</td></tr>`;
  tbl.innerHTML = h + '</tbody></table>';
  const bccEl2 = document.getElementById('bccMtx_' + country);
  if (bccEl2) bccEl2.innerHTML = buildBccMatrix(country);
}

function renderCCustomers(country) {
  if (SMALL_CTRY.has(country)) { renderSmallCCustomers(country); return; }
  const cc = document.getElementById('countryContent');
  cc.innerHTML = `<div class="card mb16"><div class="section-title">${flagImg(country)}${country} — Customers</div><div class="tbl-wrap" id="custTblC_${country}"></div></div><div id="bccMtx_${country}"></div>`;
  const tbl = document.getElementById('custTblC_' + country);
  if (!tbl) return;
  const tops = top10ByCountry[country] || [];
  const tot25=sumReal(2025,selectedMonths,country)||1, tot26=sumReal(2026,selectedMonths,country)||1;
  const totQ25=sumRealQ(2025,selectedMonths,country)||1, totQ26=sumRealQ(2026,selectedMonths,country)||1;
  const rows = tops.map(cu=>({
    cu,
    channel: cuChannelByCountry[cu]||'—',
    v24:sumCuC(country,2024,selectedMonths,cu), q24:sumCuCQ(country,2024,selectedMonths,cu),
    v25:sumCuC(country,2025,selectedMonths,cu), q25:sumCuCQ(country,2025,selectedMonths,cu),
    v26:sumCuC(country,2026,selectedMonths,cu), q26:sumCuCQ(country,2026,selectedMonths,cu),
    vBP:sumCuCBP(country,selectedMonths,cu),   qBP:sumCuCBPQ(country,selectedMonths,cu)
  })).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
  const oth={
    v25:sumCuC(country,2025,selectedMonths,'OTHERS'), q25:sumCuCQ(country,2025,selectedMonths,'OTHERS'),
    v26:sumCuC(country,2026,selectedMonths,'OTHERS'), q26:sumCuCQ(country,2026,selectedMonths,'OTHERS'),
    vBP:sumCuCBP(country,selectedMonths,'OTHERS'),   qBP:sumCuCBPQ(country,selectedMonths,'OTHERS')
  };
  let h=`<table><thead><tr><th style="width:20%">Customer</th><th style="width:9%">Channel</th><th style="width:11%">2025</th><th style="width:11%">2026 Real</th><th style="width:9%">vs 2025</th><th style="width:11%">BP 2026</th><th style="width:9%">vs BP</th><th style="width:10%">Share '25</th><th style="width:10%">Share '26</th></tr></thead><tbody>`;
  let t25=0,tQ25=0,t26=0,tQ26=0,tbp=0,tBPQ=0;
  rows.forEach(({cu,channel,v24,q24,v25,q25,v26,q26,vBP,qBP})=>{
    t25+=v25;tQ25+=q25;t26+=v26;tQ26+=q26;tbp+=vBP;tBPQ+=qBP;
    const d24=getV(v24,q24),d25=getV(v25,q25),d26=getV(v26,q26),dBP=getV(vBP,qBP);
    const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
    h+=`<tr><td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${cu}">${cu}</td>`;
    h+=`<td style="font-size:.68rem;color:var(--muted)">${channel}</td>`;
    h+=`<td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>`;
    h+=`<td>${pctPillSafe(d26,d25,d24)}</td><td>${fmtV(vBP,qBP)}</td><td>${pctPillSafeBP(d26,dBP)}</td>`;
    h+=`<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td><td>${tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
  });
  if(oth.v26>0||oth.v25>0){
    t25+=oth.v25;tQ25+=oth.q25;t26+=oth.v26;tQ26+=oth.q26;tbp+=oth.vBP;tBPQ+=oth.qBP;
    const d25=getV(oth.v25,oth.q25),d26=getV(oth.v26,oth.q26),dBP=getV(oth.vBP,oth.qBP);
    const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
    h+=`<tr style="opacity:.7"><td>OTHERS</td><td style="font-size:.68rem;color:var(--muted)">—</td>`;
    h+=`<td>${fmtV(oth.v25,oth.q25)}</td><td>${fmtV(oth.v26,oth.q26)}</td>`;
    h+=`<td>${pctPillSafe(d26,d25)}</td><td>${fmtV(oth.vBP,oth.qBP)}</td><td>${pctPillSafeBP(d26,dBP)}</td>`;
    h+=`<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td><td>${tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
  }
  const td25=getV(t25,tQ25),td26=getV(t26,tQ26);
  const realTotBP=sumBP(selectedMonths,country), realTotBPQ=sumBPQ(selectedMonths,country);
  const tdbp=getV(realTotBP,realTotBPQ);
  h+=`<tr class="total-row"><td>TOTAL</td><td></td><td>${fmtV(t25,tQ25)}</td><td>${fmtV(t26,tQ26)}</td><td>${pctPillSafe(td26,td25)}</td><td>${fmtV(realTotBP,realTotBPQ)}</td><td>${pctPillSafeBP(td26,tdbp)}</td><td>100%</td><td>100%</td></tr>`;
  tbl.innerHTML = h + '</tbody></table>';
  const bccEl = document.getElementById('bccMtx_' + country);
  if (bccEl) bccEl.innerHTML = buildBccMatrix(country);
}

function renderCBrands(country) {
  const cc = document.getElementById('countryContent');
  const wfId = 'chCWf_' + country;
  cc.innerHTML = `
    <div class="row2 mb16">
      <div class="card">
        <div class="section-title">${flagImg(country)}${country} — Brand Waterfall</div>
        <div class="chart-wrap" style="height:280px"><canvas id="${wfId}"></canvas></div>
      </div>
      <div class="card">
        <div class="section-title">Brand Detail (Brand 2)</div>
        <div class="tbl-wrap" id="b2TblC_${country}"></div>
      </div>
    </div>`;
  destroyChart(wfId);
  const el = document.getElementById(wfId);
  if (el) {
    const {labels,base,vals,colors,signed} = buildBrandWaterfall(country);
    charts[wfId] = new Chart(el, {
      type:'bar',
      data:{labels, datasets:[
        {label:'Base',data:base,backgroundColor:'transparent',stack:'w',datalabels:{display:false}},
        {label:'Value',data:vals,backgroundColor:colors,stack:'w',
          datalabels:{display:true,anchor:'end',align:'top',font:{size:9},
            formatter:(v,ctx)=>{
              const s=signed[ctx.dataIndex];
              const lbl=labels[ctx.dataIndex];
              if(['2024','2025','2026 Real','BP 2026'].includes(lbl)) return fmt(s);
              return fmtSigned(s);
            },
            color:(ctx)=>{
              const lbl=labels[ctx.dataIndex];
              if(['2024','2025','2026 Real','BP 2026'].includes(lbl)) return COLORS.text;
              return signed[ctx.dataIndex]>=0?'#10b981':'#ef4444';
            }}}
      ]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>{
          const lbl=labels[ctx.dataIndex];
          const s=signed[ctx.dataIndex];
          if(['2024','2025','2026 Real','BP 2026'].includes(lbl)) return ` ${lbl}: $${Math.round(s).toLocaleString('en-US')}`;
          return ` ${lbl}: ${fmtSigned(s)}`;
        }}}},
        scales:{x:{ticks:{color:COLORS.tick,font:{size:9}},grid:{color:COLORS.grid}},
                y:{ticks:{color:COLORS.tick,font:{size:9},callback:v=>fmtK(v)},grid:{color:COLORS.grid}}}}
    });
  }
  const tbl = document.getElementById('b2TblC_' + country);
  if (tbl) {
    const tot25=sumReal(2025,selectedMonths,country)||1, tot26=sumReal(2026,selectedMonths,country)||1;
    const totQ25=sumRealQ(2025,selectedMonths,country)||1, totQ26=sumRealQ(2026,selectedMonths,country)||1;
    const bRows = allBrand2.map(b=>({
      b,
      v25:sumB2C(country,2025,selectedMonths,b), q25:sumB2CQ(country,2025,selectedMonths,b),
      v26:sumB2C(country,2026,selectedMonths,b), q26:sumB2CQ(country,2026,selectedMonths,b),
      vBP:sumB2CBP(country,selectedMonths,b),   qBP:sumB2CBPQ(country,selectedMonths,b)
    })).filter(x=>x.v25||x.v26||x.vBP).sort((a,b2)=>b2.b==='OTHERS'?-1:a.b==='OTHERS'?1:getV(b2.v26,b2.q26)-getV(a.v26,a.q26));
    let h=`<table><thead><tr><th style="width:20%">Brand</th><th style="width:12%">2025</th><th style="width:13%">2026 Real</th><th style="width:10%">vs 2025</th><th style="width:12%">BP 2026</th><th style="width:10%">vs BP</th><th style="width:11%">Share '25</th><th style="width:12%">Share '26</th></tr></thead><tbody>`;
    let t25=0,tQ25=0,t26=0,tQ26=0,tbp=0,tBPQ=0;
    bRows.forEach(({b,v25,q25,v26,q26,vBP,qBP})=>{
      t25+=v25;tQ25+=q25;t26+=v26;tQ26+=q26;tbp+=vBP;tBPQ+=qBP;
      const d25=getV(v25,q25),d26=getV(v26,q26),dBP=getV(vBP,qBP);
      const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
      const style=b==='OTHERS'?' style="opacity:.7"':'';
      h+=`<tr${style}><td>${b}</td><td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>`;
      h+=`<td>${pctPillSafe(d26,d25)}</td><td>${fmtV(vBP,qBP)}</td><td>${pctPillSafeBP(d26,dBP)}</td>`;
      h+=`<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td><td>${tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
    });
    const td25=getV(t25,tQ25),td26=getV(t26,tQ26),tdbp=getV(tbp,tBPQ);
    h+=`<tr class="total-row"><td>TOTAL</td><td>${fmtV(t25,tQ25)}</td><td>${fmtV(t26,tQ26)}</td><td>${pctPillSafe(td26,td25)}</td><td>${fmtV(tbp,tBPQ)}</td><td>${pctPillSafeBP(td26,tdbp)}</td><td>100%</td><td>100%</td></tr>`;
    tbl.innerHTML = h + '</tbody></table>';
  }
}

function renderCFamily(country) {
  const cc = document.getElementById('countryContent');
  cc.innerHTML = `<div class="card"><div class="section-title">${flagImg(country)}${country} — Family</div><div class="tbl-wrap" id="famTblC_${country}"></div></div>`;
  const tbl = document.getElementById('famTblC_' + country);
  if (!tbl) return;
  const tot25=sumReal(2025,selectedMonths,country)||1, tot26=sumReal(2026,selectedMonths,country)||1;
  const totQ25=sumRealQ(2025,selectedMonths,country)||1, totQ26=sumRealQ(2026,selectedMonths,country)||1;
  const fRows = FAM2_ORDER.map(f=>({
    f,
    v25:sumFamC(country,2025,selectedMonths,f), q25:sumFamCQ(country,2025,selectedMonths,f),
    v26:sumFamC(country,2026,selectedMonths,f), q26:sumFamCQ(country,2026,selectedMonths,f),
    vBP:sumFamCBP(country,selectedMonths,f),   qBP:sumFamCBPQ(country,selectedMonths,f)
  })).filter(x=>x.v25||x.v26||x.vBP).sort((a,b)=>b.f==='OTHERS'?-1:a.f==='OTHERS'?1:getV(b.v26,b.q26)-getV(a.v26,a.q26));
  let h=`<table><thead><tr><th style="width:20%">Family</th><th style="width:12%">2025</th><th style="width:13%">2026 Real</th><th style="width:10%">vs 2025</th><th style="width:12%">BP 2026</th><th style="width:10%">vs BP</th><th style="width:11%">Share '25</th><th style="width:12%">Share '26</th></tr></thead><tbody>`;
  let t25=0,tQ25=0,t26=0,tQ26=0,tbp=0,tBPQ=0;
  fRows.forEach(({f,v25,q25,v26,q26,vBP,qBP})=>{
    t25+=v25;tQ25+=q25;t26+=v26;tQ26+=q26;tbp+=vBP;tBPQ+=qBP;
    const d25=getV(v25,q25),d26=getV(v26,q26),dBP=getV(vBP,qBP);
    const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
    const style=f==='OTHERS'?' style="opacity:.7"':'';
    h+=`<tr${style}><td>${f}</td><td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>`;
    h+=`<td>${pctPillSafe(d26,d25)}</td><td>${fmtV(vBP,qBP)}</td><td>${pctPillSafeBP(d26,dBP)}</td>`;
    h+=`<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td><td>${tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
  });
  const td25=getV(t25,tQ25),td26=getV(t26,tQ26),tdbp=getV(tbp,tBPQ);
  h+=`<tr class="total-row"><td>TOTAL</td><td>${fmtV(t25,tQ25)}</td><td>${fmtV(t26,tQ26)}</td><td>${pctPillSafe(td26,td25)}</td><td>${fmtV(tbp,tBPQ)}</td><td>${pctPillSafeBP(td26,tdbp)}</td><td>100%</td><td>100%</td></tr>`;
  tbl.innerHTML = h + '</tbody></table>';
}

function buildSkuTableHtml(country, skuList, labelPrefix) {
  const tot25=sumReal(2025,selectedMonths,country)||1, tot26=sumReal(2026,selectedMonths,country)||1;
  const totQ25=sumRealQ(2025,selectedMonths,country)||1, totQ26=sumRealQ(2026,selectedMonths,country)||1;
  const isTB = labelPrefix.includes('Travel Blue') || labelPrefix.includes('TB');
  const rows = skuList.map(sku=>({
    sku,
    brand:skuBrandMap[sku]||'—', cat:skuCatMap[sku]||'—',
    v24: isTB?sumSkuCTB(country,2024,selectedMonths,sku):sumSkuC(country,2024,selectedMonths,sku),
    q24: isTB?sumSkuCTBQ(country,2024,selectedMonths,sku):sumSkuCQ(country,2024,selectedMonths,sku),
    v25: isTB?sumSkuCTB(country,2025,selectedMonths,sku):sumSkuC(country,2025,selectedMonths,sku),
    q25: isTB?sumSkuCTBQ(country,2025,selectedMonths,sku):sumSkuCQ(country,2025,selectedMonths,sku),
    v26: isTB?sumSkuCTB(country,2026,selectedMonths,sku):sumSkuC(country,2026,selectedMonths,sku),
    q26: isTB?sumSkuCTBQ(country,2026,selectedMonths,sku):sumSkuCQ(country,2026,selectedMonths,sku)
  })).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
  const top24=rows.reduce((s,r)=>s+r.v24,0), topQ24=rows.reduce((s,r)=>s+r.q24,0);
  const top25=rows.reduce((s,r)=>s+r.v25,0), topQ25=rows.reduce((s,r)=>s+r.q25,0);
  const top26=rows.reduce((s,r)=>s+r.v26,0), topQ26=rows.reduce((s,r)=>s+r.q26,0);
  const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
  const topSh25=tref25>0?(getV(top25,topQ25)/tref25*100).toFixed(1)+'%':'—';
  const topSh26=tref26>0?(getV(top26,topQ26)/tref26*100).toFixed(1)+'%':'—';
  let h=`<table style="table-layout:fixed"><thead><tr><th style="width:22%;text-align:left">SKU</th><th style="width:12%">Brand</th><th style="width:13%">Category</th><th style="width:9%">2024</th><th style="width:9%">2025</th><th style="width:10%">2026 Real</th><th style="width:8%">vs 2025</th><th style="width:8%">Share '25</th><th style="width:9%">Share '26</th></tr></thead><tbody>`;
  h+=`<tr class="total-row"><td>${labelPrefix} TOTAL</td><td></td><td></td><td>${fmtV(top24,topQ24)}</td><td>${fmtV(top25,topQ25)}</td><td>${fmtV(top26,topQ26)}</td><td>${pctPillSafe(getV(top26,topQ26),getV(top25,topQ25))}</td><td>${topSh25}</td><td>${topSh26}</td></tr>`;
  rows.forEach(({sku,brand,cat,v24,q24,v25,q25,v26,q26})=>{
    const d25=getV(v25,q25),d26=getV(v26,q26);
    h+=`<tr><td style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.68rem" title="${sku}">${sku}</td>`;
    h+=`<td style="color:var(--muted);font-size:.68rem">${brand}</td>`;
    h+=`<td style="color:var(--muted);font-size:.68rem">${cat}</td>`;
    h+=`<td>${fmtV(v24,q24)}</td><td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>`;
    h+=`<td>${pctPillSafe(d26,d25)}</td>`;
    h+=`<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td>`;
    h+=`<td>${d26>0&&tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
  });
  h += '</tbody></table>';
  return h;
}

function renderCProducts(country) {
  const cc = document.getElementById('countryContent');
  const tbSkus = topTBByCountry[country] || [];
  const allSkus = topSkusByCountry[country] || [];
  let html = '';
  if (tbSkus.length > 0) {
    html += `<div class="card mb16"><div class="section-title" style="color:#3b82f6">${flagImg(country)}${country} — Top 20 SKUs (Travel Blue brand only)</div><div class="tbl-wrap" id="skuTblTB_${country}"></div></div>`;
  }
  html += `<div class="card"><div class="section-title">${flagImg(country)}${country} — Top 20 SKUs (All brands)</div><div class="tbl-wrap" id="skuTblC_${country}"></div></div>`;
  cc.innerHTML = html;
  if (tbSkus.length > 0) {
    const el = document.getElementById('skuTblTB_' + country);
    if (el) el.innerHTML = buildSkuTableHtml(country, tbSkus, 'TB TOP 20');
  }
  const tbl = document.getElementById('skuTblC_' + country);
  if (tbl) tbl.innerHTML = buildSkuTableHtml(country, allSkus, 'TOP 20');
}


function buildBrandWaterfall(country) {
  const labels = ['2024'];
  const base   = [0];
  const vals   = [];
  const colors = [];
  const signed = [];
  const v24 = BRAND4_ORDER.reduce((s,b) => s + sumB4C(2024,selectedMonths,country,b), 0);
  vals.push(v24); colors.push('#3b82f6'); signed.push(v24);
  let running = v24;
  BRAND4_ORDER.forEach(b => {
    const d = sumB4C(2025,selectedMonths,country,b) - sumB4C(2024,selectedMonths,country,b);
    labels.push(b.replace('LEXINGHAM+ANOMEO','LEX+AN'));
    base.push(d >= 0 ? running : running + d);
    vals.push(Math.abs(d)); colors.push(d >= 0 ? '#10b981' : '#ef4444');
    signed.push(d);
    running += d;
  });
  labels.push('2025'); base.push(0);
  const v25 = BRAND4_ORDER.reduce((s,b) => s + sumB4C(2025,selectedMonths,country,b), 0);
  vals.push(v25); colors.push('#3b82f6'); signed.push(v25); running = v25;
  BRAND4_ORDER.forEach(b => {
    const d = sumB4C(2026,selectedMonths,country,b) - sumB4C(2025,selectedMonths,country,b);
    labels.push(b.replace('LEXINGHAM+ANOMEO','LEX+AN'));
    base.push(d >= 0 ? running : running + d);
    vals.push(Math.abs(d)); colors.push(d >= 0 ? '#10b981' : '#ef4444');
    signed.push(d);
    running += d;
  });
  const v26 = BRAND4_ORDER.reduce((s,b) => s + sumB4C(2026,selectedMonths,country,b), 0);
  labels.push('2026 Real'); base.push(0); vals.push(v26); colors.push('#f59e0b'); signed.push(v26);
  const vBP = BRAND4_ORDER.reduce((s,b) => s + sumB4CBP(selectedMonths,country,b), 0);
  labels.push('BP 2026'); base.push(0); vals.push(vBP); colors.push('#60a5fa'); signed.push(vBP);
  return {labels, base, vals, colors, signed};
}


// ── LATAM DETAIL TAB — single page, all sections stacked ─────────────────────
function sumSkuLatam(year, months, sku) {
  const yd = skuLatamReal[year] || {};
  return months.reduce((s,mi) => s + ((yd[mi]||{})[sku]||0), 0);
}

function renderLatamDetailTab() {
  renderLDContent();
  tabDirty.latamdetail = false;
}
function renderLDContent() {
  const cc = document.getElementById('ldContent');
  cc.innerHTML = '';

  // ── Shared helpers ──────────────────────────────────────────────────────────
  function hdr(dim, hasCh) {
    const chCol = hasCh ? `<th style="width:9%">Channel</th>` : '';
    const w1 = hasCh ? '18%' : '22%';
    return `<tr><th style="width:${w1}">${dim}</th>${chCol}<th style="width:11%">2024</th><th style="width:11%">2025</th><th style="width:12%">2026 Real</th><th style="width:9%">vs 2025</th><th style="width:13%">Share '25</th><th style="width:13%">Share '26</th></tr>`;
  }
  function rowV(label, v24, q24, v25, q25, v26, q26, tot25, totQ25, tot26, totQ26, style, chLabel) {
    const s = style ? ` style="${style}"` : '';
    const d25=getV(v25,q25), d26=getV(v26,q26);
    const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
    const chCell = chLabel !== undefined ? `<td style="font-size:.68rem;color:var(--muted)">${chLabel}</td>` : '';
    return `<tr${s}><td>${label}</td>${chCell}<td>${fmtV(v24,q24)}</td><td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>` +
      `<td>${pctPillSafe(d26,d25)}</td>` +
      `<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td>` +
      `<td>${tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
  }
  function totalRowV(v24, q24, v25, q25, v26, q26, hasCh) {
    const chCell = hasCh ? '<td></td>' : '';
    const d25=getV(v25,q25), d26=getV(v26,q26);
    return `<tr class="total-row"><td>TOTAL</td>${chCell}<td>${fmtV(v24,q24)}</td><td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>` +
      `<td>${pctPillSafe(d26,d25)}</td><td>100%</td><td>100%</td></tr>`;
  }
  function section(title, tableHtml) {
    const div = document.createElement('div');
    div.className = 'card mb16';
    div.innerHTML = `<div class="section-title">${title}</div><div class="tbl-wrap">${tableHtml}</div>`;
    cc.appendChild(div);
  }

  // ── 1. CHANNELS ─────────────────────────────────────────────────────────────
  {
    const chRows=CHANNELS.map(ch=>({
      ch,
      v24:sumDim(chReal,2024,selectedMonths,ch), q24:sumDimQ(chRealQ,2024,selectedMonths,ch),
      v25:sumDim(chReal,2025,selectedMonths,ch), q25:sumDimQ(chRealQ,2025,selectedMonths,ch),
      v26:sumDim(chReal,2026,selectedMonths,ch), q26:sumDimQ(chRealQ,2026,selectedMonths,ch)
    })).filter(x=>x.v24||x.v25||x.v26).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
    const t=chRows.reduce((a,x)=>({v24:a.v24+x.v24,q24:a.q24+x.q24,v25:a.v25+x.v25,q25:a.q25+x.q25,v26:a.v26+x.v26,q26:a.q26+x.q26}),{v24:0,q24:0,v25:0,q25:0,v26:0,q26:0});
    const tot25=t.v25||1, totQ25=t.q25||1, tot26=t.v26||1, totQ26=t.q26||1;
    let h=`<table><thead>${hdr('Channel',false)}</thead><tbody>`;
    chRows.forEach(({ch,v24,q24,v25,q25,v26,q26})=>{ h+=rowV(ch,v24,q24,v25,q25,v26,q26,tot25,totQ25,tot26,totQ26); });
    h+=totalRowV(t.v24,t.q24,t.v25,t.q25,t.v26,t.q26,false);
    section('🛒 Channels',h+'</tbody></table>');
  }

  // ── 2. CUSTOMERS (TOP 15) ────────────────────────────────────────────────────
  {
    const tot25=sumLatam(2025,selectedMonths)||1, totQ25=sumLatamQ(2025,selectedMonths)||1;
    const tot26=sumLatam(2026,selectedMonths)||1, totQ26=sumLatamQ(2026,selectedMonths)||1;
    const named=top15Customers.map(cu=>({
      cu,
      ch: cuChannelMap[cu]||'—',
      v24:sumDim(cuReal,2024,selectedMonths,cu), q24:sumDimQ(cuRealQ,2024,selectedMonths,cu),
      v25:sumDim(cuReal,2025,selectedMonths,cu), q25:sumDimQ(cuRealQ,2025,selectedMonths,cu),
      v26:sumDim(cuReal,2026,selectedMonths,cu), q26:sumDimQ(cuRealQ,2026,selectedMonths,cu)
    })).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
    const oth={
      v24:sumDim(cuReal,2024,selectedMonths,'OTHERS'), q24:sumDimQ(cuRealQ,2024,selectedMonths,'OTHERS'),
      v25:sumDim(cuReal,2025,selectedMonths,'OTHERS'), q25:sumDimQ(cuRealQ,2025,selectedMonths,'OTHERS'),
      v26:sumDim(cuReal,2026,selectedMonths,'OTHERS'), q26:sumDimQ(cuRealQ,2026,selectedMonths,'OTHERS')
    };
    let h=`<table><thead>${hdr('Customer',true)}</thead><tbody>`;
    let tv24=0,tq24=0,tv25=0,tq25=0,tv26=0,tq26=0;
    named.forEach(({cu,ch,v24,q24,v25,q25,v26,q26})=>{
      tv24+=v24;tq24+=q24;tv25+=v25;tq25+=q25;tv26+=v26;tq26+=q26;
      const lbl=`<span title="${cu}" style="display:inline-block;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom">${cu}</span>`;
      h+=rowV(lbl,v24,q24,v25,q25,v26,q26,tot25,totQ25,tot26,totQ26,'',ch);
    });
    tv24+=oth.v24;tq24+=oth.q24;tv25+=oth.v25;tq25+=oth.q25;tv26+=oth.v26;tq26+=oth.q26;
    h+=rowV('OTHERS',oth.v24,oth.q24,oth.v25,oth.q25,oth.v26,oth.q26,tot25,totQ25,tot26,totQ26,'opacity:.7','—');
    h+=totalRowV(tv24,tq24,tv25,tq25,tv26,tq26,true);
    section('👥 Top 15 Customers',h+'</tbody></table>');
  }

  // ── 3. BRAND ─────────────────────────────────────────────────────────────────
  {
    const bRows=allBrand2.map(b=>({
      b,
      v24:sumDim(b2Real,2024,selectedMonths,b), q24:sumDimQ(b2RealQ,2024,selectedMonths,b),
      v25:sumDim(b2Real,2025,selectedMonths,b), q25:sumDimQ(b2RealQ,2025,selectedMonths,b),
      v26:sumDim(b2Real,2026,selectedMonths,b), q26:sumDimQ(b2RealQ,2026,selectedMonths,b)
    })).filter(x=>x.v24||x.v25||x.v26);
    const named=bRows.filter(x=>x.b!=='OTHERS').sort((a,b2)=>getV(b2.v26,b2.q26)-getV(a.v26,a.q26));
    const othB=bRows.find(x=>x.b==='OTHERS')||{b:'OTHERS',v24:0,q24:0,v25:0,q25:0,v26:0,q26:0};
    const t=bRows.reduce((a,x)=>({v24:a.v24+x.v24,q24:a.q24+x.q24,v25:a.v25+x.v25,q25:a.q25+x.q25,v26:a.v26+x.v26,q26:a.q26+x.q26}),{v24:0,q24:0,v25:0,q25:0,v26:0,q26:0});
    const tot25=t.v25||1, totQ25=t.q25||1, tot26=t.v26||1, totQ26=t.q26||1;
    let h=`<table><thead>${hdr('Brand',false)}</thead><tbody>`;
    named.forEach(({b,v24,q24,v25,q25,v26,q26})=>{ h+=rowV(b,v24,q24,v25,q25,v26,q26,tot25,totQ25,tot26,totQ26); });
    if(othB.v24||othB.v25||othB.v26) h+=rowV('OTHERS',othB.v24,othB.q24,othB.v25,othB.q25,othB.v26,othB.q26,tot25,totQ25,tot26,totQ26,'opacity:.7');
    h+=totalRowV(t.v24,t.q24,t.v25,t.q25,t.v26,t.q26,false);
    section('🏷️ Brand',h+'</tbody></table>');
  }

  // ── 4. FAMILY ────────────────────────────────────────────────────────────────
  {
    const allFamKeys=new Set([...FAM2_ORDER,
      ...Object.values(famReal).flatMap(yr=>Object.values(yr).flatMap(m=>Object.keys(m)))]);
    const fRows=[...allFamKeys].map(f=>({
      f,
      v24:sumDim(famReal,2024,selectedMonths,f), q24:sumDimQ(famRealQ,2024,selectedMonths,f),
      v25:sumDim(famReal,2025,selectedMonths,f), q25:sumDimQ(famRealQ,2025,selectedMonths,f),
      v26:sumDim(famReal,2026,selectedMonths,f), q26:sumDimQ(famRealQ,2026,selectedMonths,f)
    })).filter(x=>x.v24||x.v25||x.v26)
      .sort((a,b)=>b.f==='OTHERS'?-1:a.f==='OTHERS'?1:getV(b.v26,b.q26)-getV(a.v26,a.q26));
    const t=fRows.reduce((a,x)=>({v24:a.v24+x.v24,q24:a.q24+x.q24,v25:a.v25+x.v25,q25:a.q25+x.q25,v26:a.v26+x.v26,q26:a.q26+x.q26}),{v24:0,q24:0,v25:0,q25:0,v26:0,q26:0});
    const tot25=t.v25||1, totQ25=t.q25||1, tot26=t.v26||1, totQ26=t.q26||1;
    let h=`<table><thead>${hdr('Family',false)}</thead><tbody>`;
    fRows.forEach(({f,v24,q24,v25,q25,v26,q26})=>{
      h+=rowV(f,v24,q24,v25,q25,v26,q26,tot25,totQ25,tot26,totQ26,f==='OTHERS'?'opacity:.7':'');
    });
    h+=totalRowV(t.v24,t.q24,t.v25,t.q25,t.v26,t.q26,false);
    section('📦 Family',h+'</tbody></table>');
  }

  // ── 5. SKU TOP 20 ────────────────────────────────────────────────────────────
  function buildLatamSkuTable(skuList, labelPfx) {
    const tot25=sumLatam(2025,selectedMonths)||1, tot26=sumLatam(2026,selectedMonths)||1;
    const totQ25=sumLatamQ(2025,selectedMonths)||1, totQ26=sumLatamQ(2026,selectedMonths)||1;
    const isTB=labelPfx.includes('Travel Blue')||labelPfx.includes('TB');
    const rows=skuList.map(sku=>({
      sku, brand:skuBrandMap[sku]||'—', cat:skuCatMap[sku]||'—',
      v24:isTB?sumSkuLatamTB(2024,selectedMonths,sku):sumSkuLatam(2024,selectedMonths,sku),
      q24:isTB?sumSkuLatamTBQ(2024,selectedMonths,sku):sumSkuLatamQ(2024,selectedMonths,sku),
      v25:isTB?sumSkuLatamTB(2025,selectedMonths,sku):sumSkuLatam(2025,selectedMonths,sku),
      q25:isTB?sumSkuLatamTBQ(2025,selectedMonths,sku):sumSkuLatamQ(2025,selectedMonths,sku),
      v26:isTB?sumSkuLatamTB(2026,selectedMonths,sku):sumSkuLatam(2026,selectedMonths,sku),
      q26:isTB?sumSkuLatamTBQ(2026,selectedMonths,sku):sumSkuLatamQ(2026,selectedMonths,sku)
    })).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
    const T24=rows.reduce((s,r)=>s+r.v24,0), TQ24=rows.reduce((s,r)=>s+r.q24,0);
    const T25=rows.reduce((s,r)=>s+r.v25,0), TQ25=rows.reduce((s,r)=>s+r.q25,0);
    const T26=rows.reduce((s,r)=>s+r.v26,0), TQ26=rows.reduce((s,r)=>s+r.q26,0);
    const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
    const topSh25=tref25>0?(getV(T25,TQ25)/tref25*100).toFixed(1)+'%':'—';
    const topSh26=tref26>0?(getV(T26,TQ26)/tref26*100).toFixed(1)+'%':'—';
    let h=`<table style="table-layout:fixed"><thead><tr><th style="width:22%;text-align:left">SKU</th><th style="width:12%">Brand</th><th style="width:13%">Category</th><th style="width:9%">2024</th><th style="width:9%">2025</th><th style="width:10%">2026 Real</th><th style="width:8%">vs 2025</th><th style="width:8%">Share '25</th><th style="width:9%">Share '26</th></tr></thead><tbody>`;
    h+=`<tr class="total-row"><td>${labelPfx} TOTAL</td><td></td><td></td><td>${fmtV(T24,TQ24)}</td><td>${fmtV(T25,TQ25)}</td><td>${fmtV(T26,TQ26)}</td><td>${pctPillSafe(getV(T26,TQ26),getV(T25,TQ25))}</td><td>${topSh25}</td><td>${topSh26}</td></tr>`;
    rows.forEach(({sku,brand,cat,v24,q24,v25,q25,v26,q26})=>{
      const d25=getV(v25,q25),d26=getV(v26,q26);
      h+=`<tr><td style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.68rem" title="${sku}">${sku}</td>`;
      h+=`<td style="color:var(--muted);font-size:.68rem">${brand}</td><td style="color:var(--muted);font-size:.68rem">${cat}</td>`;
      h+=`<td>${fmtV(v24,q24)}</td><td>${fmtV(v25,q25)}</td><td>${fmtV(v26,q26)}</td>`;
      h+=`<td>${pctPillSafe(d26,d25)}</td>`;
      h+=`<td>${tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}</td>`;
      h+=`<td>${d26>0&&tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}</td></tr>`;
    });
    return h+'</tbody></table>';
  }
  // Travel Blue Top 20 first
  if(top20LatamTB.length>0) {
    section('🔷 Top 20 SKUs — Travel Blue Brand Only', buildLatamSkuTable(top20LatamTB,'TB TOP 20'));
  }
  // General Top 20
  section('🔖 Top 20 SKUs — All Brands', buildLatamSkuTable(top20Latam,'TOP 20'));
}

// ── PDF EXPORT ────────────────────────────────────────────────────────────────
function exportPDF() {
  const btn = document.getElementById('pdfBtn');
  btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Generating...';
  btn.disabled = true;

  // Capture the full page body
  const target = document.body;
  html2canvas(target, {
    scale: 1.5,
    useCORS: true,
    allowTaint: true,
    logging: false,
    backgroundColor: '#0f172a',
    scrollX: 0,
    scrollY: 0,
    windowWidth: document.documentElement.scrollWidth,
    windowHeight: document.documentElement.scrollHeight
  }).then(canvas => {
    const { jsPDF } = window.jspdf;
    const imgData = canvas.toDataURL('image/jpeg', 0.92);
    const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const imgH  = (canvas.height * pageW) / canvas.width;
    let remaining = imgH;
    let yPos = 0;
    pdf.addImage(imgData, 'JPEG', 0, yPos, pageW, imgH);
    remaining -= pageH;
    while (remaining > 0) {
      yPos -= pageH;
      pdf.addPage();
      pdf.addImage(imgData, 'JPEG', 0, yPos, pageW, imgH);
      remaining -= pageH;
    }
    const tabName = document.querySelector('.tab-btn.active')?.textContent?.trim() || 'dashboard';
    pdf.save(`LATAM_${tabName.replace(/\s+/g,'_')}_2026.pdf`);
    btn.innerHTML = '<i class="bi bi-file-earmark-pdf"></i> Export PDF';
    btn.disabled = false;
  }).catch(err => {
    console.error(err);
    btn.innerHTML = '<i class="bi bi-file-earmark-pdf"></i> Export PDF';
    btn.disabled = false;
  });
}

// ── INIT ──────────────────────────────────────────────────────────────────────
buildMonthButtons();
renderKPIs();
renderSummary();
</script>
</body>
</html>
"""

OUTPUT.write_text(html, encoding='utf-8')
print(f"Done! Output: {OUTPUT}")
print(f"File size: {OUTPUT.stat().st_size / 1024:.0f} KB")
# Also write to original folder
OUTPUT2 = BASE_DIR / "Business Review LATAM 2026.html"
OUTPUT2.write_text(html, encoding='utf-8')
print(f"Also written to: {OUTPUT2}")
