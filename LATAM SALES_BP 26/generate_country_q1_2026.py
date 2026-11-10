#!/usr/bin/env python3
"""
Generate country-specific Q1 2026 dashboards for MEXICO and BRAZIL.
Run: python generate_country_q1_2026.py
Outputs: Business Review Mexico 2026.html  |  Business Review Brasil 2026.html
"""
import pandas as pd, json, numpy as np
from pathlib import Path
import urllib.request, base64 as _b64

BASE_DIR  = Path(r"C:\Users\Soporte\OneDrive - Travel Blue\Ambiente de Trabalho\Dashboards Camila\travel-blue-dashboards\LATAM SALES_BP 26")
EXCEL     = BASE_DIR / "ANALISE Q1 2026 2.xlsx"
SC2_FILE  = BASE_DIR / "ANALISE Q1 2026 SCENARIO 2.xlsx"

YEARS_HIST    = [2018,2019,2020,2021,2022,2023,2024,2025]
MONTHS_PT     = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
MONTH_IDX     = {m:i for i,m in enumerate(MONTHS_PT)}
SC2_EFFECTS   = {'ARGENTINA':'Exchange Rate Effect','BRAZIL':'Unicross Brand Effect',
                 'PANAMA':'Month Billing Adjustment','MEXICO':'Maxell Brand Effect'}
VALID_CH      = {'DOMESTIC','RETAIL','ONLINE','OTHER'}
BRAND4_ORDER  = ['TRAVEL BLUE','CLOE','LEXINGHAM+ANOMEO','OTHERS']
BRAND4_COLORS = {'TRAVEL BLUE':'#3b82f6','CLOE':'#f59e0b','LEXINGHAM+ANOMEO':'#10b981','OTHERS':'#94a3b8'}
BRAND4_ORDER_BY_COUNTRY = {
    'BRAZIL': ['TRAVEL BLUE','SLOOTH','LEXINGHAM+ANOMEO','OTHERS'],
    'MEXICO': ['TRAVEL BLUE','CLOE','LEXINGHAM+ANOMEO','OTHERS'],
}
BRAND4_COLORS_BY_COUNTRY = {
    'BRAZIL': {'TRAVEL BLUE':'#3b82f6','SLOOTH':'#8b5cf6','LEXINGHAM+ANOMEO':'#10b981','OTHERS':'#94a3b8'},
    'MEXICO': {'TRAVEL BLUE':'#3b82f6','CLOE':'#f59e0b','LEXINGHAM+ANOMEO':'#10b981','OTHERS':'#94a3b8'},
}
TARGET        = ['MEXICO','BRAZIL']
FLAG_CODES    = {'MEXICO':'mx','BRAZIL':'br'}

# ── Load & prep ────────────────────────────────────────────────────────────────
print("Reading Excel…")
df = pd.read_excel(EXCEL, sheet_name='SALES_SYSTEM_DATABASE')
print(f"  {len(df)} rows.")

def fix_b(b):
    if pd.isna(b): return 'OTHERS'
    s = str(b)
    return 'ANOMEO' if ('AN' in s and 'MEO' in s) else s

df['BRAND3'] = df['BRAND 3'].apply(fix_b)
df['BRAND4'] = df['BRAND3'].apply(lambda b:
    'TRAVEL BLUE' if b=='TRAVEL BLUE' else 'CLOE' if b=='CLOE' else
    'SLOOTH' if b=='SLOOTH' else
    'LEXINGHAM+ANOMEO' if b in ('LEXINGHAM','ANOMEO') else 'OTHERS')
df['CHANNEL'] = df['CHANNEL'].fillna('OTHER').str.strip()
df['YEAR']   = pd.to_numeric(df['YEAR'], errors='coerce').astype('Int64')
df = df[df['YEAR'].notna()].copy(); df['YEAR'] = df['YEAR'].astype(int)
df['SKU 2']  = df['SKU 2'].astype(str)  # normalise: column has mixed int/str values
df['midx']   = df['MONTH'].map(MONTH_IDX)
df = df[df['midx'].notna()].copy(); df['midx'] = df['midx'].astype(int)
df['FAM2']   = df['FAMILY 2'].apply(lambda f: 'OTHERS' if pd.isna(f) else
               ('ANOMEO' if ('AN' in str(f) and 'MEO' in str(f)) else str(f)))
amt = 'NET AMOUNT (USD)'
real_df = df[df['TYPE']=='REAL'].copy()
bp_df   = df[df['TYPE']=='BP 26'].copy()

# ── SC2 ───────────────────────────────────────────────────────────────────────
print("Loading SC2…")
sc2r = pd.read_excel(SC2_FILE, sheet_name='Planilha1')
sc2r = sc2r[sc2r['TYPE']=='SCENARIO 2'].copy()
sc2r['YEAR'] = pd.to_numeric(sc2r['YEAR'], errors='coerce').astype(int)
sc2r['midx'] = pd.to_numeric(sc2r['MONTH'], errors='coerce') - 1
sc2r = sc2r[sc2r['midx'].between(0,11)].copy(); sc2r['midx'] = sc2r['midx'].astype(int)
sc2M_full = {}
for _, row in sc2r.iterrows():
    yr=int(row['YEAR']); mi=int(row['midx']); c=str(row['COUNTRY'])
    v=float(row[amt]) if pd.notna(row[amt]) else 0.0
    sc2M_full.setdefault(yr,{}).setdefault(mi,{})[c] = sc2M_full.get(yr,{}).get(mi,{}).get(c,0)+v

# ── Flags ─────────────────────────────────────────────────────────────────────
print("Fetching flags…")
flags = {}
for c,code in FLAG_CODES.items():
    try:
        with urllib.request.urlopen(f'https://flagcdn.com/32x24/{code}.png', timeout=10) as r:
            flags[c] = 'data:image/png;base64,' + _b64.b64encode(r.read()).decode()
        print(f"  {c} OK")
    except Exception as e:
        flags[c] = ''; print(f"  {c} FAILED: {e}")

# ── Per-country data builder ──────────────────────────────────────────────────
def build_data(country):
    r  = real_df[real_df['COUNTRY']==country].copy()
    b  = bp_df[bp_df['COUNTRY']==country].copy()
    cr = r[r['CHANNEL'].isin(VALID_CH)].copy()
    cb = b[b['CHANNEL'].isin(VALID_CH)].copy()

    def ym(sub):
        out={}
        for (yr,mi),v in sub.groupby(['YEAR','midx'])[amt].sum().items():
            out.setdefault(int(yr),{})[int(mi)]=round(float(v),2)
        return out
    def bm(sub):
        return {int(mi):round(float(v),2) for mi,v in sub.groupby('midx')[amt].sum().items()}
    def ymd(sub,col):
        out={}
        for (yr,mi,d),v in sub.groupby(['YEAR','midx',col])[amt].sum().items():
            out.setdefault(int(yr),{}).setdefault(int(mi),{})[str(d)]=round(float(v),2)
        return out
    def bmd(sub,col):
        out={}
        for (mi,d),v in sub.groupby(['midx',col])[amt].sum().items():
            out.setdefault(int(mi),{})[str(d)]=round(float(v),2)
        return out

    realM  = ym(r);  bpM   = bm(b)
    chReal = ymd(cr,'CHANNEL'); chBP = bmd(cb,'CHANNEL')
    b4Real = ymd(r,'BRAND4');   b4BP = bmd(b,'BRAND4')
    famReal= ymd(r,'FAM2');     famBP= bmd(b,'FAM2')

    qty_col = 'QTY'
    def ymq(sub):
        out={}
        for (yr,mi),v in sub.groupby(['YEAR','midx'])[qty_col].sum().items():
            out.setdefault(int(yr),{})[int(mi)]=round(float(v),2)
        return out
    def bmq(sub):
        return {int(mi):round(float(v),2) for mi,v in sub.groupby('midx')[qty_col].sum().items()}
    def ymdq(sub,col):
        out={}
        for (yr,mi,d),v in sub.groupby(['YEAR','midx',col])[qty_col].sum().items():
            out.setdefault(int(yr),{}).setdefault(int(mi),{})[str(d)]=round(float(v),2)
        return out
    def bmdq(sub,col):
        out={}
        for (mi,d),v in sub.groupby(['midx',col])[qty_col].sum().items():
            out.setdefault(int(mi),{})[str(d)]=round(float(v),2)
        return out

    realMQ  = ymq(r);  bpMQ   = bmq(b)
    chRealQ = ymdq(cr,'CHANNEL'); chBPQ = bmdq(cb,'CHANNEL')
    b4RealQ = ymdq(r,'BRAND4');   b4BPQ = bmdq(b,'BRAND4')
    famRealQ= ymdq(r,'FAM2');     famBPQ= bmdq(b,'FAM2')

    # Customers — build corrected CUSTOMER→CUSTOMER3 map (BP-side takes priority,
    # handles cases like Havan whose REAL rows have CUSTOMER3='OTHERS' but BP row has CUSTOMER3='HAVAN')
    _cu3_combo = pd.concat([b[['CUSTOMER','CUSTOMER 3']], r[['CUSTOMER','CUSTOMER 3']]])
    _cu3_combo = _cu3_combo.copy()
    _cu3_combo['CUSTOMER']   = _cu3_combo['CUSTOMER'].astype(str)
    _cu3_combo['CUSTOMER 3'] = _cu3_combo['CUSTOMER 3'].astype(str)
    _cu3_named = _cu3_combo[~_cu3_combo['CUSTOMER 3'].isin(['OTHERS','nan',''])]
    cu3_fix_map = _cu3_named.groupby('CUSTOMER')['CUSTOMER 3'].first().to_dict()

    # top10 = top 10 "named-with-BP" customers by total REAL sales
    r2=r.copy(); b2=b.copy()
    r2['CK'] = r2['CUSTOMER'].astype(str).map(cu3_fix_map).fillna('OTHERS')
    b2['CK'] = b2['CUSTOMER'].astype(str).map(cu3_fix_map).fillna('OTHERS')
    _named_ck = r2[r2['CK'] != 'OTHERS']
    top10 = [str(x) for x in _named_ck.groupby('CK')[amt].sum().nlargest(10).index]
    r2['CK'] = r2['CK'].apply(lambda x: x if x in top10 else 'OTHERS')
    b2['CK'] = b2['CK'].apply(lambda x: x if x in top10 else 'OTHERS')
    cuReal=ymd(r2,'CK'); cuBP=bmd(b2,'CK')
    cuRealQ=ymdq(r2,'CK'); cuBPQ=bmdq(b2,'CK')

    # Customer → channel map (use CK-corrected lookup)
    cu_channel_map = {}
    for _cu in top10:
        _sub = r2[r2['CK'] == _cu]
        _ch_mode = _sub['CHANNEL'].dropna().value_counts()
        cu_channel_map[_cu] = str(_ch_mode.index[0]) if len(_ch_mode) > 0 else '—'

    # Extra top-10 customers WITHOUT BP projection (sub-level breakout under Others)
    _r26 = r[r['YEAR'] == 2026]
    _cu26_sales = _r26.groupby('CUSTOMER')[amt].sum()
    _top10_raw = [str(c) for c in _cu26_sales.nlargest(10).index]
    _extra_cu = [c for c in _top10_raw if cu3_fix_map.get(c, 'OTHERS') == 'OTHERS']
    _r_extra = r[r['CUSTOMER'].astype(str).isin(_extra_cu)].copy()
    _r_extra['CUSTOMER'] = _r_extra['CUSTOMER'].astype(str)
    extraCuReal = {}
    for (yr,mi,cu),v in _r_extra.groupby(['YEAR','midx','CUSTOMER'])[amt].sum().items():
        extraCuReal.setdefault(int(yr),{}).setdefault(int(mi),{})[str(cu)] = round(float(v),2)
    extraCuRealQ = {}
    for (yr,mi,cu),v in _r_extra.groupby(['YEAR','midx','CUSTOMER'])[qty_col].sum().items():
        extraCuRealQ.setdefault(int(yr),{}).setdefault(int(mi),{})[str(cu)] = round(float(v),2)
    extraCuChannelMap = {}
    for _c in _extra_cu:
        _sub_c = _r_extra[_r_extra['CUSTOMER']==_c]
        _ch = _sub_c['CHANNEL'].dropna().value_counts()
        extraCuChannelMap[_c] = str(_ch.index[0]) if len(_ch)>0 else '—'

    # All-customer data for "Vendas por Cliente" tab
    _r_allcu = r.copy()
    _r_allcu['CUSTOMER'] = _r_allcu['CUSTOMER'].astype(str)
    allCuReal = {}
    for (yr,mi,cu),v in _r_allcu.groupby(['YEAR','midx','CUSTOMER'])[amt].sum().items():
        allCuReal.setdefault(int(yr),{}).setdefault(int(mi),{})[str(cu)] = round(float(v),2)
    allCuRealQ = {}
    for (yr,mi,cu),v in _r_allcu.groupby(['YEAR','midx','CUSTOMER'])[qty_col].sum().items():
        allCuRealQ.setdefault(int(yr),{}).setdefault(int(mi),{})[str(cu)] = round(float(v),2)
    _r26_allcu = _r_allcu[_r_allcu['YEAR']==2026]
    allCuList = [str(c) for c in _r26_allcu.groupby('CUSTOMER')[amt].sum().sort_values(ascending=False).index]
    _cu_other_yrs = [str(c) for c in _r_allcu[_r_allcu['YEAR'].isin([2024,2025])].groupby('CUSTOMER')[amt].sum().sort_values(ascending=False).index if str(c) not in allCuList]
    allCuList = allCuList + _cu_other_yrs

    # Customer → channel map for ALL customers (used for filters in "Sales / Customer" tab)
    allCuChannelMap = {}
    for _cu, _grp in _r_allcu.groupby('CUSTOMER'):
        _ch = _grp['CHANNEL'].dropna().value_counts()
        allCuChannelMap[str(_cu)] = str(_ch.index[0]) if len(_ch) > 0 else '—'

    # SKUs top 20
    r25_all=r[r['YEAR']==2025]
    top20=[str(s) for s in r25_all.groupby('SKU 2')[amt].sum().nlargest(20).index]
    sku_cat={}; sku_brd={}
    for sku in top20:
        s=r[r['SKU 2']==sku]
        c_=s['CATEGORY'].dropna().mode(); bx=s['BRAND 2'].dropna().mode()
        sku_cat[sku]=str(c_.iloc[0]) if len(c_)>0 else '—'
        sku_brd[sku]=str(bx.iloc[0]) if len(bx)>0 else '—'
    sk=r[r['SKU 2'].isin(top20)]
    skuReal={}
    for (yr,mi,sku),v in sk.groupby(['YEAR','midx','SKU 2'])[amt].sum().items():
        skuReal.setdefault(int(yr),{}).setdefault(int(mi),{})[str(sku)]=round(float(v),2)
    bk=b[b['SKU 2'].isin(top20)]
    skuBP={}
    for (mi,sku),v in bk.groupby(['midx','SKU 2'])[amt].sum().items():
        skuBP.setdefault(int(mi),{})[str(sku)]=round(float(v),2)
    skuRealQ={}
    for (yr,mi,sku),v in sk.groupby(['YEAR','midx','SKU 2'])[qty_col].sum().items():
        skuRealQ.setdefault(int(yr),{}).setdefault(int(mi),{})[str(sku)]=round(float(v),2)

    # Travel Blue top 20 — ranked by 2026 Real sales (primary), fallback to 2025
    r26_all = r[r['YEAR']==2026]
    r26_tb = r26_all[r26_all['BRAND 2']=='TRAVEL BLUE']
    r25_tb = r25_all[r25_all['BRAND 2']=='TRAVEL BLUE']
    _tops26 = list(r26_tb.groupby('SKU 2')[amt].sum().nlargest(20).index)
    if len(_tops26) < 20:
        _tops25 = [s for s in r25_tb.groupby('SKU 2')[amt].sum().nlargest(20).index if s not in _tops26]
        _tops26 = _tops26 + _tops25[:20 - len(_tops26)]
    top20_tb = [str(s) for s in _tops26]
    all_skus = set(top20)|set(top20_tb)
    for sku in all_skus - set(sku_cat.keys()):
        s=r[r['SKU 2']==sku]
        c_=s['CATEGORY'].dropna().mode(); bx=s['BRAND 2'].dropna().mode()
        sku_cat[sku]=str(c_.iloc[0]) if len(c_)>0 else '—'
        sku_brd[sku]=str(bx.iloc[0]) if len(bx)>0 else '—'
    sk_tb=r[r['SKU 2'].isin(top20_tb)]
    skuRealTB={}
    for (yr,mi,sku),v in sk_tb.groupby(['YEAR','midx','SKU 2'])[amt].sum().items():
        skuRealTB.setdefault(int(yr),{}).setdefault(int(mi),{})[str(sku)]=round(float(v),2)
    skuRealTBQ={}
    for (yr,mi,sku),v in sk_tb.groupby(['YEAR','midx','SKU 2'])[qty_col].sum().items():
        skuRealTBQ.setdefault(int(yr),{}).setdefault(int(mi),{})[str(sku)]=round(float(v),2)
    skuRealQAll={}
    for (yr,mi,sku),v in r[r['SKU 2'].isin(all_skus)].groupby(['YEAR','midx','SKU 2'])[qty_col].sum().items():
        skuRealQAll.setdefault(int(yr),{}).setdefault(int(mi),{})[str(sku)]=round(float(v),2)

    # Brand × Category × Customer matrix
    _cs_bcc = r.copy()
    _cs_bcc['_BC'] = _cs_bcc['BRAND 2'].fillna('OTHERS').astype(str) + '|||' + _cs_bcc['CATEGORY'].fillna('OTHERS').astype(str)
    _cu_col_bcc = 'CUSTOMER'
    _r25_bcc = _cs_bcc[_cs_bcc['YEAR']==2025]
    bccTops_c = {}
    for _bck, _grp in _r25_bcc.groupby('_BC'):
        _t=[str(x) for x in _grp.groupby(_cu_col_bcc)[amt].sum().nlargest(10).index
            if str(x) not in ('nan','None','','OTHERS')]
        if _t: bccTops_c[str(_bck)]=_t
    for _bck, _grp in _cs_bcc[_cs_bcc['YEAR']==2026].groupby('_BC'):
        if str(_bck) not in bccTops_c:
            _t=[str(x) for x in _grp.groupby(_cu_col_bcc)[amt].sum().nlargest(10).index
                if str(x) not in ('nan','None','','OTHERS')]
            if _t: bccTops_c[str(_bck)]=_t
    _all_bcc_cu_c={x for v in bccTops_c.values() for x in v}
    _cs_f_bcc=_cs_bcc[_cs_bcc[_cu_col_bcc].isin(_all_bcc_cu_c)]
    bccReal_c={}
    for (yr,mi,bc,cu),val in _cs_f_bcc.groupby(['YEAR','midx','_BC',_cu_col_bcc])[amt].sum().items():
        _bcs,_cus=str(bc),str(cu)
        if _cus in bccTops_c.get(_bcs,[]):
            bccReal_c.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_bcs,{})[_cus]=round(float(val),2)
    bccRealQ_c={}
    for (yr,mi,bc,cu),val in _cs_f_bcc.groupby(['YEAR','midx','_BC',_cu_col_bcc])[qty_col].sum().items():
        _bcs,_cus=str(bc),str(cu)
        if _cus in bccTops_c.get(_bcs,[]):
            bccRealQ_c.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_bcs,{})[_cus]=round(float(val),2)

    # Customer × Brand hierarchy
    _cs_cb = r.copy()
    _r25_cb = _cs_cb[_cs_cb['YEAR']==2025]
    cb_tops_c = [str(x) for x in _r25_cb.groupby('CUSTOMER')[amt].sum().nlargest(10).index
                 if str(x) not in ('nan','None','','OTHERS')]
    for _cux in _cs_cb[_cs_cb['YEAR']==2026]['CUSTOMER'].dropna().unique():
        if str(_cux) not in ('nan','None','','OTHERS') and str(_cux) not in cb_tops_c:
            cb_tops_c.append(str(_cux))
    _cs_cb_f = _cs_cb[_cs_cb['CUSTOMER'].isin(set(cb_tops_c))]
    cbReal_c2={}
    for (yr,mi,cu,b2),val in _cs_cb_f.groupby(['YEAR','midx','CUSTOMER','BRAND 2'])[amt].sum().items():
        _cu_s,_b2_s=str(cu),str(b2)
        if _cu_s in cb_tops_c:
            cbReal_c2.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_b2_s]=round(float(val),2)
    cbRealQ_c2={}
    for (yr,mi,cu,b2),val in _cs_cb_f.groupby(['YEAR','midx','CUSTOMER','BRAND 2'])[qty_col].sum().items():
        _cu_s,_b2_s=str(cu),str(b2)
        if _cu_s in cb_tops_c:
            cbRealQ_c2.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_b2_s]=round(float(val),2)
    _cs_cb_tb = _cs_cb_f[_cs_cb_f['BRAND 2']=='TRAVEL BLUE']
    cbcTBReal_c={}
    for (yr,mi,cu,cat),val in _cs_cb_tb.groupby(['YEAR','midx','CUSTOMER','CATEGORY'])[amt].sum().items():
        _cu_s,_cat_s=str(cu),str(cat)
        if _cu_s in cb_tops_c:
            cbcTBReal_c.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_cat_s]=round(float(val),2)
    cbcTBRealQ_c={}
    for (yr,mi,cu,cat),val in _cs_cb_tb.groupby(['YEAR','midx','CUSTOMER','CATEGORY'])[qty_col].sum().items():
        _cu_s,_cat_s=str(cu),str(cat)
        if _cu_s in cb_tops_c:
            cbcTBRealQ_c.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_cat_s]=round(float(val),2)
    # Customer × TB × FAMILY × CATEGORY USD
    _cbfcReal_c = {}
    for (yr,mi,cu,fam,cat),val in _cs_cb_tb.groupby(['YEAR','midx','CUSTOMER','FAMILY','CATEGORY'])[amt].sum().items():
        _cu_s,_fam_s,_cat_s=str(cu),str(fam),str(cat)
        if _cu_s in cb_tops_c:
            _cbfcReal_c.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{}).setdefault(_fam_s,{})[_cat_s]=round(float(val),2)
    # Customer × TB × FAMILY × CATEGORY QTY
    _cbfcRealQ_c = {}
    for (yr,mi,cu,fam,cat),val in _cs_cb_tb.groupby(['YEAR','midx','CUSTOMER','FAMILY','CATEGORY'])[qty_col].sum().items():
        _cu_s,_fam_s,_cat_s=str(cu),str(fam),str(cat)
        if _cu_s in cb_tops_c:
            _cbfcRealQ_c.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{}).setdefault(_fam_s,{})[_cat_s]=round(float(val),2)
    # Customer × TB × FAMILY USD
    _cbfReal_c = {}
    for (yr,mi,cu,fam),val in _cs_cb_tb.groupby(['YEAR','midx','CUSTOMER','FAMILY'])[amt].sum().items():
        _cu_s,_fam_s=str(cu),str(fam)
        if _cu_s in cb_tops_c:
            _cbfReal_c.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_fam_s]=round(float(val),2)
    # Customer × TB × FAMILY QTY
    _cbfRealQ_c = {}
    for (yr,mi,cu,fam),val in _cs_cb_tb.groupby(['YEAR','midx','CUSTOMER','FAMILY'])[qty_col].sum().items():
        _cu_s,_fam_s=str(cu),str(fam)
        if _cu_s in cb_tops_c:
            _cbfRealQ_c.setdefault(int(yr),{}).setdefault(int(mi),{}).setdefault(_cu_s,{})[_fam_s]=round(float(val),2)

    # SC2
    sc2M={}; sc2Diff={}
    for yr in YEARS_HIST+[2026]:
        for mi in range(12):
            val=sc2M_full.get(yr,{}).get(mi,{}).get(country)
            if val is not None:
                sc2M.setdefault(yr,{})[mi]=round(val,2)
    for yr in YEARS_HIST+[2026]:
        diffs=[]
        for mi in range(12):
            sc2v=sc2M.get(yr,{}).get(mi)
            if sc2v is not None:
                rv=realM.get(yr,{}).get(mi,0)
                if abs(sc2v-rv)>0.01: diffs.append(mi)
        if diffs: sc2Diff[str(yr)]=diffs

    return dict(realM=realM,bpM=bpM,chReal=chReal,chBP=chBP,
                b4Real=b4Real,b4BP=b4BP,famReal=famReal,famBP=famBP,
                cuReal=cuReal,cuBP=cuBP,top10=top10,
                top20=top20,skuReal=skuReal,skuBP=skuBP,
                sku_cat=sku_cat,sku_brd=sku_brd,
                sc2M=sc2M,sc2Diff=sc2Diff,
                realMQ=realMQ,bpMQ=bpMQ,
                chRealQ=chRealQ,chBPQ=chBPQ,
                b4RealQ=b4RealQ,b4BPQ=b4BPQ,
                famRealQ=famRealQ,famBPQ=famBPQ,
                cuRealQ=cuRealQ,cuBPQ=cuBPQ,
                cu_channel_map=cu_channel_map,
                top20_tb=top20_tb,
                skuRealTB=skuRealTB,skuRealTBQ=skuRealTBQ,
                skuRealQ=skuRealQ,skuRealQAll=skuRealQAll,
                bccTops=bccTops_c,bccReal=bccReal_c,bccRealQ=bccRealQ_c,
                cbTops=cb_tops_c,cbReal=cbReal_c2,cbRealQ=cbRealQ_c2,
                cbcTBReal=cbcTBReal_c,cbcTBRealQ=cbcTBRealQ_c,
                cbfReal=_cbfReal_c, cbfRealQ=_cbfRealQ_c,
                cbfcReal=_cbfcReal_c, cbfcRealQ=_cbfcRealQ_c,
                extra_cu_list=_extra_cu,
                extra_cu_real=extraCuReal, extra_cu_realQ=extraCuRealQ,
                extra_cu_channel_map=extraCuChannelMap,
                all_cu_real=allCuReal, all_cu_realQ=allCuRealQ,
                all_cu_list=allCuList,
                all_cu_channel_map=allCuChannelMap)

# ── HTML generator ─────────────────────────────────────────────────────────────
def generate_html(country, d):
    flag_uri = flags.get(country,'')
    effect   = SC2_EFFECTS.get(country,'')
    flag_img = f'<img src="{flag_uri}" width="24" height="18" style="border-radius:2px;vertical-align:middle;margin-right:6px">' if flag_uri else ''

    def jv(name, obj): return f"const {name} = {json.dumps(obj, ensure_ascii=False)};"

    js_data = "\n".join([
        jv("realM",    d['realM']),
        jv("bpM",      d['bpM']),
        jv("chReal",   d['chReal']),
        jv("chBP",     d['chBP']),
        jv("b4Real",   d['b4Real']),
        jv("b4BP",     d['b4BP']),
        jv("famReal",  d['famReal']),
        jv("famBP",    d['famBP']),
        jv("cuReal",   d['cuReal']),
        jv("cuBP",     d['cuBP']),
        jv("top10",    d['top10']),
        jv("top20",    d['top20']),
        jv("skuReal",  d['skuReal']),
        jv("skuBP",    d['skuBP']),
        jv("skuCatMap",d['sku_cat']),
        jv("skuBrdMap",d['sku_brd']),
        jv("sc2M",     d['sc2M']),
        jv("sc2Diff",  d['sc2Diff']),
        f"const COUNTRY  = {json.dumps(country)};",
        f"const FLAG_URI = {json.dumps(flag_uri)};",
        f"const EFFECT   = {json.dumps(effect)};",
        jv("BRAND4_ORDER",  BRAND4_ORDER_BY_COUNTRY.get(country, BRAND4_ORDER)),
        jv("BRAND4_COLORS", BRAND4_COLORS_BY_COUNTRY.get(country, BRAND4_COLORS)),
        jv("YEARS_HIST",    YEARS_HIST),
        # QTY structures
        jv("realMQ",    d['realMQ']),
        jv("bpMQ",      d['bpMQ']),
        jv("chRealQ",   d['chRealQ']),
        jv("chBPQ",     d['chBPQ']),
        jv("b4RealQ",   d['b4RealQ']),
        jv("b4BPQ",     d['b4BPQ']),
        jv("famRealQ",  d['famRealQ']),
        jv("famBPQ",    d['famBPQ']),
        jv("cuRealQ",   d['cuRealQ']),
        jv("cuBPQ",     d['cuBPQ']),
        jv("cuChannelMap", d['cu_channel_map']),
        # Travel Blue SKUs
        jv("top20TB",      d['top20_tb']),
        jv("skuRealTB",    d['skuRealTB']),
        jv("skuRealTBQ",   d['skuRealTBQ']),
        jv("skuRealQ",     d['skuRealQ']),
        jv("skuRealQAll",  d['skuRealQAll']),
        jv("bccTops",      d['bccTops']),
        jv("bccReal",      d['bccReal']),
        jv("bccRealQ",     d['bccRealQ']),
        jv("cbTops",       d['cbTops']),
        jv("cbReal",       d['cbReal']),
        jv("cbRealQ",      d['cbRealQ']),
        jv("cbcTBReal",    d['cbcTBReal']),
        jv("cbcTBRealQ",   d['cbcTBRealQ']),
        jv("cbfReal",    d['cbfReal']),
        jv("cbfRealQ",   d['cbfRealQ']),
        jv("cbfcReal",   d['cbfcReal']),
        jv("cbfcRealQ",  d['cbfcRealQ']),
        # Extra top-10 no-BP customers (sub-level under Others)
        jv("extraCuList",       d['extra_cu_list']),
        jv("extraCuReal",       d['extra_cu_real']),
        jv("extraCuRealQ",      d['extra_cu_realQ']),
        jv("extraCuChannelMap", d['extra_cu_channel_map']),
        # All-customer data for Sales / Customer tab
        jv("allCuReal",  d['all_cu_real']),
        jv("allCuRealQ", d['all_cu_realQ']),
        jv("allCuList",  d['all_cu_list']),
        jv("allCuChannelMap", d['all_cu_channel_map']),
    ])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Business Review {country} 2026</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-datalabels/2.2.0/chartjs-plugin-datalabels.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<style>
:root{{
  --bg:#0a0e1a;--card:#111827;--border:#1e293b;--text:#e2e8f0;--accent:#f59e0b;
  --hdr:#0d1424;--tab-active:#f59e0b;--tbl-head:#1e293b;--total-bg:#1e3a2e;--total-clr:#34d399;
  --muted:#94a3b8;--green:#10b981;--red:#ef4444;--blue:#3b82f6;
}}
.light-mode{{
  --bg:#f1f4f9;--card:#fff;--border:#dde3ec;--text:#1e293b;--accent:#113d85;
  --hdr:#113d85;--tab-active:#113d85;--tbl-head:#113d85;--total-bg:#dcfce7;--total-clr:#166534;
  --muted:#64748b;--green:#15803d;--red:#b91c1c;--blue:#1d4ed8;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}}
.hdr{{background:var(--hdr);padding:12px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}}
.hdr-title{{font-size:1.1rem;font-weight:700;color:var(--accent);white-space:nowrap;display:flex;align-items:center;gap:8px}}
.hdr-kpis{{display:flex;gap:16px;flex-wrap:wrap}}
.kpi-item{{text-align:center}}
.kpi-label{{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}}
.kpi-val{{font-size:.95rem;font-weight:700;color:var(--text)}}
.kpi-pct{{font-size:.8rem;font-weight:600}}
.pct-pos{{color:var(--green)}}.pct-neg{{color:var(--red)}}.pct-neu{{color:var(--muted)}}
.hdr-actions{{display:flex;gap:8px;align-items:center}}
.btn-theme{{background:transparent;border:1px solid var(--border);color:var(--text);border-radius:6px;padding:4px 10px;cursor:pointer;font-size:.8rem}}
.month-strip{{background:var(--hdr);border-bottom:1px solid var(--border);padding:8px 20px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;position:sticky;top:57px;z-index:99}}
.month-strip-label{{font-size:.7rem;color:var(--muted);text-transform:uppercase;margin-right:4px;white-space:nowrap}}
.mth-btn{{padding:3px 10px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.75rem;transition:all .15s}}
.mth-btn.active{{background:var(--accent);color:#000;border-color:var(--accent);font-weight:600}}
.mth-btn:hover:not(.active){{border-color:var(--accent);color:var(--accent)}}
.strip-ctrl{{display:flex;gap:4px;margin-left:4px}}
.strip-ctrl button{{padding:2px 8px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.7rem}}
.tabs-bar{{display:flex;gap:0;border-bottom:1px solid var(--border);background:var(--hdr);padding:0 20px;overflow-x:auto;position:sticky;top:97px;z-index:98}}
.tab-btn{{display:flex;align-items:center;gap:6px;padding:10px 16px;cursor:pointer;border:none;background:transparent;color:var(--muted);font-size:.85rem;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s}}
.tab-btn.active{{color:var(--tab-active);border-bottom-color:var(--tab-active);font-weight:600}}
.tab-btn:hover:not(.active){{color:var(--text)}}
.tab-content{{display:none;padding:20px;max-width:100%;overflow-x:hidden}}.tab-content.active{{display:block}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px}}
.chart-wrap{{position:relative;width:100%}}
.section-title{{font-size:.9rem;font-weight:600;color:var(--accent);margin-bottom:12px;padding-bottom:4px;border-bottom:1px solid var(--border)}}
.tbl-wrap{{overflow-x:hidden}}
table{{width:100%;border-collapse:collapse;font-size:.72rem;table-layout:fixed}}
th{{background:var(--tbl-head);color:#fff;padding:6px 7px;text-align:right;white-space:normal;word-break:break-word;position:sticky;top:0;line-height:1.2}}
.light-mode th{{color:#fff}}
th:first-child{{text-align:left;width:22%}}
td{{padding:5px 7px;border-bottom:1px solid var(--border);text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
td:first-child{{text-align:left}}
tr:hover td{{background:rgba(255,255,255,.03)}}
tr.total-row td{{background:var(--total-bg);color:var(--total-clr);font-weight:700}}
.pill{{display:inline-block;padding:1px 6px;border-radius:10px;font-size:.72rem;font-weight:600}}
.pill.pos{{background:#064e3b;color:#34d399}}.pill.neg{{background:#450a0a;color:#fca5a5}}
.light-mode .pill.pos{{background:#dcfce7;color:#166534}}.light-mode .pill.neg{{background:#fee2e2;color:#b91c1c}}
.mb16{{margin-bottom:16px}}.mb8{{margin-bottom:8px}}.mt12{{margin-top:12px}}
.row2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;min-width:0}}.row2>.card{{min-width:0;overflow:hidden}}
@media(max-width:600px){{.row2{{grid-template-columns:1fr}}}}
.hero-card{{background:linear-gradient(120deg,rgba(245,158,11,.12),rgba(59,130,246,.08));border:2px solid var(--accent);border-radius:14px;padding:18px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:16px;margin-bottom:16px}}
.hero-flag{{font-size:2.4rem;line-height:1}}
.hero-name{{font-size:1.3rem;font-weight:800;color:var(--accent)}}
.hero-sub{{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.8px}}
.hero-metric{{text-align:center;flex:1 1 110px;padding:10px 14px;border-radius:10px;background:rgba(255,255,255,.04)}}
.hero-metric-lbl{{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}}
.hero-metric-val{{font-size:1.5rem;font-weight:800;color:var(--text);line-height:1.1}}
.hero-metric-pct{{display:inline-block;margin-top:5px;padding:2px 10px;border-radius:20px;font-size:.78rem;font-weight:700}}
.hero-metric-pct.pos{{background:rgba(16,185,129,.2);color:#10b981}}
.hero-metric-pct.neg{{background:rgba(239,68,68,.2);color:#ef4444}}
.hero-metric-pct.neu{{color:var(--muted);font-size:.72rem}}
.sc2-detail{{margin-top:8px;overflow-x:auto}}
.sc2-detail table{{font-size:.72rem}}
.sc2-detail th{{font-size:.7rem;background:var(--border);color:var(--text)}}
.sc2-legend{{font-size:.7rem;color:var(--muted);margin-top:4px}}
.sc2-legend span{{display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b;margin-right:4px;vertical-align:middle}}
.hist-kpis{{display:flex;gap:14px;padding:5px 8px;background:rgba(255,255,255,.03);border-radius:6px;margin-top:4px}}
.hist-kpi-item{{display:flex;align-items:center;gap:4px;font-size:.73rem}}
.hist-kpi-lbl{{color:var(--muted)}}.hist-kpi-val{{font-weight:700}}
.hist-kpi-val.pos{{color:var(--green)}}.hist-kpi-val.neg{{color:var(--red)}}.hist-kpi-val.neu{{color:var(--muted)}}
img.flag-img{{border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.35);vertical-align:middle}}
.view-toggle{{display:flex;gap:3px;margin-left:8px}}
.vbtn{{padding:3px 11px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.72rem;transition:all .15s;white-space:nowrap}}
.vbtn.active{{background:var(--accent);color:#000;border-color:var(--accent);font-weight:700}}
.vbtn:hover:not(.active){{border-color:var(--accent);color:var(--accent)}}
.pill.new-item{{background:#1e3a5f;color:#60a5fa}}
.light-mode .pill.new-item{{background:#dbeafe;color:#1d4ed8}}
</style>
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
</head>
<body>
<div class="hdr">
  <div class="hdr-title">{flag_img}<span>{country} Sales &amp; BP 2026</span></div>
  <div class="hdr-kpis" id="hdrKpis"></div>
  <div class="hdr-actions">
    <button class="btn-theme" onclick="toggleTheme()"><i class="bi bi-circle-half"></i> Theme</button>
  </div>
</div>
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
  <button onclick="exportExcel()" style="margin-left:auto;padding:3px 13px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.72rem;display:flex;align-items:center;gap:5px;white-space:nowrap;transition:all .15s" onmouseover="this.style.borderColor='#16a34a';this.style.color='#16a34a'" onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--muted)'">
    <i class="bi bi-file-earmark-excel"></i> Export Excel
  </button>
  <button id="pdfBtn" onclick="exportPDF()" style="padding:3px 13px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.72rem;display:flex;align-items:center;gap:5px;white-space:nowrap;transition:all .15s" onmouseover="this.style.borderColor='var(--accent)';this.style.color='var(--accent)'" onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--muted)'">
    <i class="bi bi-file-earmark-pdf"></i> Export PDF
  </button>
</div>
<div class="tabs-bar">
  <button class="tab-btn active" onclick="switchTab('overview',this)"><i class="bi bi-grid"></i> Overview</button>
  <button class="tab-btn" onclick="switchTab('historical',this)"><i class="bi bi-graph-up-arrow"></i> Historical</button>
  <button class="tab-btn" onclick="switchTab('channels',this)"><i class="bi bi-shop"></i> Channels</button>
  <button class="tab-btn" onclick="switchTab('brands',this)"><i class="bi bi-tags-fill"></i> Brands</button>
  <button class="tab-btn" onclick="switchTab('family',this)"><i class="bi bi-grid-3x3-gap-fill"></i> Family</button>
  <button class="tab-btn" onclick="switchTab('products',this)"><i class="bi bi-upc-scan"></i> Products</button>
  <button class="tab-btn" onclick="switchTab('customers',this)"><i class="bi bi-people-fill"></i> Customers</button>
  <button class="tab-btn" onclick="switchTab('salescust',this)"><i class="bi bi-table"></i> Sales / Customer</button>
  <button class="tab-btn" onclick="switchTab('custbrand',this)"><i class="bi bi-diagram-3-fill"></i> Customer — Brand</button>
</div>

<div id="tab-overview"  class="tab-content active"><div id="overviewContent"></div></div>
<div id="tab-historical" class="tab-content"><div id="histContent"></div></div>
<div id="tab-channels"  class="tab-content"><div id="chContent"></div></div>
<div id="tab-brands"    class="tab-content"><div id="b4Content"></div></div>
<div id="tab-family"    class="tab-content"><div id="famContent"></div></div>
<div id="tab-products"  class="tab-content"><div id="skuContent"></div></div>
<div id="tab-customers" class="tab-content"><div id="cuContent"></div></div>
<div id="tab-salescust" class="tab-content"><div id="salesCustContent"></div></div>
<div id="tab-custbrand" class="tab-content"><div id="cbContent"></div></div>

<script>
Chart.register(ChartDataLabels);
{js_data}

const MONTHS_EN = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const CH_COLORS = {{DOMESTIC:'#3b82f6',RETAIL:'#f59e0b',ONLINE:'#10b981',OTHER:'#8b5cf6'}};
let selectedMonths = [0,1,2,3,4,5,6,7,8,9]; // Default: Jan-Aug (YTD)
let currentTab = 'overview';
let charts = {{}};
let tabDirty = {{historical:true,channels:true,brands:true,family:true,products:true,customers:true,salescust:true,custbrand:true}};
let COLORS = {{grid:'#1e293b',tick:'#94a3b8',text:'#e2e8f0'}};
let viewMode = 'usd'; // 'usd' | 'qty' | 'avg'

function setViewMode(m) {{
  viewMode = m;
  ['USD','QTY','AVG'].forEach(x => {{
    const b = document.getElementById('vbtn'+x);
    if (b) b.classList.toggle('active', x.toLowerCase() === m);
  }});
  updateAll();
}}

function refreshColors(){{
  const dark = !document.body.classList.contains('light-mode');
  COLORS.grid = dark?'#1e293b':'#e2e8f0';
  COLORS.tick = dark?'#94a3b8':'#64748b';
  COLORS.text = dark?'#e2e8f0':'#1e293b';
}}

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmt(v){{ return v==null?'—':'$'+Math.round(v).toLocaleString('en-US'); }}
function fmtK(v){{ if(v==null)return''; const a=Math.abs(v); return a>=1000000?(v/1000000).toFixed(1)+'M':(v/1000).toFixed(0)+'K'; }}
function fmtSigned(v){{ return (v>=0?'+':'')+fmt(v); }}
function safePct(v,ref){{ if(!ref||Math.abs(ref)<0.01)return null; return ((v-ref)/ref*100).toFixed(1); }}
function pctPill(p){{
  if(p==null)return'<span class="pill neu">—</span>';
  const cls=+p>=0?'pos':'neg'; return `<span class="pill ${{cls}}">${{+p>=0?'+':''}}${{p}}%</span>`;
}}
function pctPillSafe(v26,v25,v24) {{
  v24=v24||0;
  if (!v25 || Math.abs(v25) < 0.01) {{
    if (v26 > 0 && Math.abs(v24) < 0.01) return '<span class="pill new-item">NEW</span>';
    return '<span class="pill" style="background:transparent;color:var(--muted)">—</span>';
  }}
  return pctPill(safePct(v26,v25));
}}
function pctPillSafeBP(v26,vBP) {{
  if (!vBP || Math.abs(vBP) < 0.01) return '<span class="pill" style="background:transparent;color:var(--muted)">—</span>';
  return pctPill(safePct(v26,vBP));
}}
function pctPillTight(v26,v25,v24) {{
  v24=v24||0;
  if (!v25 || Math.abs(v25) < 0.01) {{
    if (v26 > 0 && Math.abs(v24) < 0.01) return '<span class="pill new-item">NEW</span>';
    return '<span class="pill" style="background:transparent;color:var(--muted)">—</span>';
  }}
  return pctPill(((v26-v25)/Math.abs(v25)*100).toFixed(1));
}}
function fmtV(usd,qty) {{
  if(viewMode==='qty') return (qty==null||isNaN(qty))?'—':Math.round(qty).toLocaleString('en-US')+' pcs';
  if(viewMode==='avg') return (qty>0&&usd!=null&&!isNaN(usd))?'$'+(usd/qty).toFixed(2):'—';
  return fmt(usd);
}}
function fmtVK(usd,qty) {{
  if(viewMode==='qty') return (qty==null||isNaN(qty))?'':Math.round(qty).toLocaleString('en-US');
  if(viewMode==='avg') return (qty>0&&usd!=null)?'$'+(usd/qty).toFixed(2):'';
  return fmtK(usd);
}}
function getV(usd,qty) {{
  return viewMode==='qty'?qty:viewMode==='avg'?(qty>0?usd/qty:0):usd;
}}
function fmtChartLbl(v) {{
  if (v==null||isNaN(v)||v===0) return '';
  if (viewMode==='qty') {{
    const a=Math.abs(v);
    return a>=1000000?(v/1000000).toFixed(1)+'M':a>=1000?(v/1000).toFixed(0)+'K':Math.round(v).toString();
  }}
  if (viewMode==='avg') return '$'+v.toFixed(2);
  const a=Math.abs(v);
  return a>=1000000?'$'+(v/1000000).toFixed(1)+'M':'$'+Math.round(v/1000)+'K';
}}
function fmtChartTooltip(v) {{
  if (v==null||isNaN(v)) return '—';
  if (viewMode==='qty') return Math.round(v).toLocaleString('en-US')+' pcs';
  if (viewMode==='avg') return '$'+v.toFixed(2);
  return '$'+Math.round(v).toLocaleString('en-US');
}}
function sumBccR(year,months,bc,cu){{
  const yd=bccReal[year]||{{}};
  return months.reduce((s,mi)=>s+((((yd[mi]||{{}})[bc])||{{}})[cu]||0),0);
}}
function sumBccRQ(year,months,bc,cu){{
  const yd=bccRealQ[year]||{{}};
  return months.reduce((s,mi)=>s+((((yd[mi]||{{}})[bc])||{{}})[cu]||0),0);
}}
// QTY sum helpers
function sumRealQ(year,months){{
  const yd=realMQ[year]||{{}};
  return months.reduce((s,mi)=>s+(yd[mi]||0),0);
}}
function sumBPQ(months){{
  return months.reduce((s,mi)=>s+(bpMQ[mi]||0),0);
}}
function sumDimQ(dataObj,year,months,dim){{
  const yd=dataObj[year]||{{}};
  return months.reduce((s,mi)=>s+((yd[mi]||{{}})[dim]||0),0);
}}
function sumDimBPQf(bpObj,months,dim){{
  return months.reduce((s,mi)=>s+((bpObj[mi]||{{}})[dim]||0),0);
}}
function sumSkuQ(year,months,sku){{
  const yd=skuRealQ[year]||{{}};
  return months.reduce((s,mi)=>s+((yd[mi]||{{}})[sku]||0),0);
}}
function sumSkuTBQ(year,months,sku){{
  const yd=skuRealTBQ[year]||{{}};
  return months.reduce((s,mi)=>s+((yd[mi]||{{}})[sku]||0),0);
}}
function sumSkuTB(year,months,sku){{
  const yd=skuRealTB[year]||{{}};
  return months.reduce((s,mi)=>s+((yd[mi]||{{}})[sku]||0),0);
}}

function sumReal(year, months){{
  const yd=realM[year]||{{}};
  return months.reduce((s,mi)=>s+(yd[mi]||0),0);
}}
function sumBP(months){{
  return months.reduce((s,mi)=>s+(bpM[mi]||0),0);
}}
function sumSC2(year, months){{
  const yd=sc2M[year]||{{}};
  return months.reduce((s,mi)=>{{
    const v=yd[mi];
    return s+(v!=null?v:((realM[year]||{{}})[mi]||0));
  }},0);
}}
function sumDim(data, year, months, dim){{
  const yd=data[year]||{{}};
  return months.reduce((s,mi)=>s+((yd[mi]||{{}})[dim]||0),0);
}}
function sumBPDim(data, months, dim){{
  return months.reduce((s,mi)=>s+((data[mi]||{{}})[dim]||0),0);
}}
function sc2HasAdj(year){{
  const diff=(sc2Diff[String(year)]||[]);
  return diff.some(mi=>selectedMonths.includes(mi));
}}
function sumCbR(year,months,cu,brand){{
  const yd=cbReal[year]||{{}};
  return months.reduce((s,mi)=>s+((((yd[mi]||{{}})[cu])||{{}})[brand]||0),0);
}}
function sumCbRQ(year,months,cu,brand){{
  const yd=cbRealQ[year]||{{}};
  return months.reduce((s,mi)=>s+((((yd[mi]||{{}})[cu])||{{}})[brand]||0),0);
}}
function sumCbcTBR(year,months,cu,cat){{
  const yd=cbcTBReal[year]||{{}};
  return months.reduce((s,mi)=>s+((((yd[mi]||{{}})[cu])||{{}})[cat]||0),0);
}}
function sumCbcTBRQ(year,months,cu,cat){{
  const yd=cbcTBRealQ[year]||{{}};
  return months.reduce((s,mi)=>s+((((yd[mi]||{{}})[cu])||{{}})[cat]||0),0);
}}
function sumCuTotCb(year,months,cu){{
  const yd=cbReal[year]||{{}};
  return months.reduce((s,mi)=>{{const bd=(yd[mi]||{{}})[cu]||{{}};return s+Object.values(bd).reduce((a,b)=>a+b,0);}},0);
}}
function sumCuTotCbQ(year,months,cu){{
  const yd=cbRealQ[year]||{{}};
  return months.reduce((s,mi)=>{{const bd=(yd[mi]||{{}})[cu]||{{}};return s+Object.values(bd).reduce((a,b)=>a+b,0);}},0);
}}
function getBrandsForCuR(cu){{
  const brands=new Set();
  Object.values(cbReal).forEach(yd=>Object.values(yd).forEach(md=>Object.keys(md[cu]||{{}}).forEach(b=>brands.add(b))));
  return [...brands];
}}
function getCatsForCuTBR(cu){{
  const cats=new Set();
  Object.values(cbcTBReal).forEach(yd=>Object.values(yd).forEach(md=>Object.keys(md[cu]||{{}}).forEach(c=>cats.add(c))));
  return [...cats];
}}
function sumCbfam(year,months,cu,fam){{
  const yd=(cbfReal[year]||{{}});
  return months.reduce((s,mi)=>s+((((yd[mi]||{{}})[cu])||{{}})[fam]||0),0);
}}
function sumCbfamQ(year,months,cu,fam){{
  const yd=(cbfRealQ[year]||{{}});
  return months.reduce((s,mi)=>s+((((yd[mi]||{{}})[cu])||{{}})[fam]||0),0);
}}
function sumCbfamCat(year,months,cu,fam,cat){{
  const yd=(cbfcReal[year]||{{}});
  return months.reduce((s,mi)=>s+(((((yd[mi]||{{}})[cu])||{{}})[fam]||{{}})[cat]||0),0);
}}
function sumCbfamCatQ(year,months,cu,fam,cat){{
  const yd=(cbfcRealQ[year]||{{}});
  return months.reduce((s,mi)=>s+(((((yd[mi]||{{}})[cu])||{{}})[fam]||{{}})[cat]||0),0);
}}
function getFamsTB(cu){{
  const fams=new Set();
  Object.values(cbfReal).forEach(yd=>Object.values(yd).forEach(md=>Object.keys((md[cu]||{{}})).forEach(f=>fams.add(f))));
  return [...fams];
}}
function getCatsForFamTB(cu,fam){{
  const cats=new Set();
  Object.values(cbfcReal).forEach(yd=>Object.values(yd).forEach(md=>Object.keys(((md[cu]||{{}})[fam]||{{}})).forEach(c=>cats.add(c))));
  return [...cats];
}}

function renderCustBrand(){{
  const el=document.getElementById('cbContent');
  if(!el) return;
  const allCus=cbTops||[];
  const cuRows=allCus.map(cu=>{{
    const v25=sumCuTotCb(2025,selectedMonths,cu),q25=sumCuTotCbQ(2025,selectedMonths,cu);
    const v26=sumCuTotCb(2026,selectedMonths,cu),q26=sumCuTotCbQ(2026,selectedMonths,cu);
    return {{cu,v25,q25,v26,q26}};
  }}).filter(x=>x.v25>0||x.v26>0).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26)).slice(0,5);
  if(!cuRows.length){{el.innerHTML='<p style="color:var(--muted);padding:20px">No data.</p>';tabDirty.custbrand=false;return;}}
  const ctryV25=sumReal(2025,selectedMonths)||1,ctryV26=sumReal(2026,selectedMonths)||1;
  const ctryQ25=sumRealQ(2025,selectedMonths)||1,ctryQ26=sumRealQ(2026,selectedMonths)||1;
  const HDR=`<tr><th style="width:36%;text-align:left">Customer / Brand / Category</th><th style="width:12%">2025</th><th style="width:13%">2026 Real</th><th style="width:10%">vs 2025</th><th style="width:14%">Share '25</th><th style="width:15%">Share '26</th></tr>`;
  let h=`<table><thead>${{HDR}}</thead><tbody>`;
  cuRows.forEach(({{cu,v25,q25,v26,q26}})=>{{
    const d25=getV(v25,q25),d26=getV(v26,q26);
    const ref25=getV(ctryV25,ctryQ25)||1,ref26=getV(ctryV26,ctryQ26)||1;
    h+=`<tr style="background:rgba(245,158,11,.08)"><td style="font-weight:700;font-size:.74rem;padding:5px 7px">${{cu}}</td><td style="font-weight:600">${{fmtV(v25,q25)}}</td><td style="font-weight:600">${{fmtV(v26,q26)}}</td><td>${{pctPillTight(d26,d25)}}</td><td style="font-weight:600">${{ref25>0?(d25/ref25*100).toFixed(1)+'%':'—'}}</td><td style="font-weight:600">${{ref26>0?(d26/ref26*100).toFixed(1)+'%':'—'}}</td></tr>`;
    const brands=getBrandsForCuR(cu);
    const brandRows=brands.map(b=>{{const bv25=sumCbR(2025,selectedMonths,cu,b),bq25=sumCbRQ(2025,selectedMonths,cu,b),bv26=sumCbR(2026,selectedMonths,cu,b),bq26=sumCbRQ(2026,selectedMonths,cu,b);return {{b,v25:bv25,q25:bq25,v26:bv26,q26:bq26}};}})
      .filter(x=>x.v25>0||x.v26>0).sort((a,b2)=>getV(b2.v26,b2.q26)-getV(a.v26,a.q26));
    const cuRef25=d25||1,cuRef26=d26||1;
    brandRows.forEach(({{b,v25:bv25,q25:bq25,v26:bv26,q26:bq26}})=>{{
      const bd25=getV(bv25,bq25),bd26=getV(bv26,bq26);
      h+=`<tr><td style="padding-left:22px;font-size:.72rem"><span style="color:var(--muted);margin-right:4px">▸</span>${{b}}</td><td>${{fmtV(bv25,bq25)}}</td><td>${{fmtV(bv26,bq26)}}</td><td>${{pctPillTight(bd26,bd25)}}</td><td>${{cuRef25>0?(bd25/cuRef25*100).toFixed(1)+'%':'—'}}</td><td>${{cuRef26>0?(bd26/cuRef26*100).toFixed(1)+'%':'—'}}</td></tr>`;
      if (b==='TRAVEL BLUE') {{
        const fams=getFamsTB(cu);
        const famRows=fams.map(fam=>({{fam,v25:sumCbfam(2025,selectedMonths,cu,fam),q25:sumCbfamQ(2025,selectedMonths,cu,fam),v26:sumCbfam(2026,selectedMonths,cu,fam),q26:sumCbfamQ(2026,selectedMonths,cu,fam)}}))
          .filter(x=>x.v25>0||x.v26>0).sort((a,c2)=>getV(c2.v26,c2.q26)-getV(a.v26,a.q26));
        const tbRef25=bd25||1, tbRef26=bd26||1;
        famRows.forEach(({{fam,v25:fv25,q25:fq25,v26:fv26,q26:fq26}})=>{{
          const fd25=getV(fv25,fq25),fd26=getV(fv26,fq26);
          h+=`<tr style="background:rgba(16,185,129,.05)"><td style="padding-left:42px;font-size:.7rem;color:#6ee7b7"><span style="margin-right:4px">◆</span>${{fam}}</td><td>${{fmtV(fv25,fq25)}}</td><td>${{fmtV(fv26,fq26)}}</td><td>${{pctPillTight(fd26,fd25)}}</td><td>${{tbRef25>0?(fd25/tbRef25*100).toFixed(1)+'%':'—'}}</td><td>${{tbRef26>0?(fd26/tbRef26*100).toFixed(1)+'%':'—'}}</td></tr>`;
          const famCats=getCatsForFamTB(cu,fam);
          const catRows=famCats.map(cat=>({{cat,v25:sumCbfamCat(2025,selectedMonths,cu,fam,cat),q25:sumCbfamCatQ(2025,selectedMonths,cu,fam,cat),v26:sumCbfamCat(2026,selectedMonths,cu,fam,cat),q26:sumCbfamCatQ(2026,selectedMonths,cu,fam,cat)}}))
            .filter(x=>x.v25>0||x.v26>0).sort((a,c2)=>getV(c2.v26,c2.q26)-getV(a.v26,a.q26));
          catRows.forEach(({{cat,v25:cv25,q25:cq25,v26:cv26,q26:cq26}})=>{{
            const cd25=getV(cv25,cq25),cd26=getV(cv26,cq26);
            h+=`<tr style="background:rgba(59,130,246,.04)"><td style="padding-left:62px;font-size:.68rem;color:var(--muted)"><span style="margin-right:4px">•</span>${{cat}}</td><td>${{fmtV(cv25,cq25)}}</td><td>${{fmtV(cv26,cq26)}}</td><td>${{pctPillTight(cd26,cd25)}}</td><td>${{fd25>0?(cd25/fd25*100).toFixed(1)+'%':'—'}}</td><td>${{fd26>0?(cd26/fd26*100).toFixed(1)+'%':'—'}}</td></tr>`;
          }});
        }});
      }}
    }});
  }});
  h+='</tbody></table>';
  el.innerHTML=`<div class="card"><div class="section-title"><i class="bi bi-diagram-3-fill"></i> ${{COUNTRY}} — Customer × Brand × Category (Top 5)</div><div class="tbl-wrap">${{h}}</div></div>`;
  tabDirty.custbrand=false;
}}

function buildBccMatrix(){{
  const bcKeys=Object.keys(bccTops);
  if(!bcKeys.length) return '';
  const bcData=bcKeys.map(bc=>{{
    const tops=bccTops[bc];
    const v26=tops.reduce((s,cu)=>s+sumBccR(2026,selectedMonths,bc,cu),0);
    const v25=tops.reduce((s,cu)=>s+sumBccR(2025,selectedMonths,bc,cu),0);
    const q26=tops.reduce((s,cu)=>s+sumBccRQ(2026,selectedMonths,bc,cu),0);
    const q25=tops.reduce((s,cu)=>s+sumBccRQ(2025,selectedMonths,bc,cu),0);
    return {{bc,tops,v26,v25,q26,q25}};
  }}).filter(x=>x.v26>0||x.v25>0).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
  if(!bcData.length) return '';
  let html=`<div class="card mt12"><div class="section-title"><i class="bi bi-grid-3x3-gap-fill"></i> Top 5 Customers by Brand \u00d7 Category</div><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:12px;margin-top:10px">`;
  bcData.forEach(({{bc,tops}})=>{{
    const [brand,cat]=bc.split('|||');
    const rows=tops.map(cu=>{{
      return {{cu,
        v25:sumBccR(2025,selectedMonths,bc,cu),q25:sumBccRQ(2025,selectedMonths,bc,cu),
        v26:sumBccR(2026,selectedMonths,bc,cu),q26:sumBccRQ(2026,selectedMonths,bc,cu)}};
    }}).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26)).slice(0,5)
      .filter(r=>r.v25>0||r.v26>0);
    if(!rows.length) return;
    const tot25=rows.reduce((s,r)=>s+getV(r.v25,r.q25),0)||1;
    const tot26=rows.reduce((s,r)=>s+getV(r.v26,r.q26),0)||1;
    html+=`<div><div style="font-size:.75rem;font-weight:700;color:var(--accent);margin-bottom:4px;padding:3px 8px;background:rgba(245,158,11,.08);border-left:3px solid var(--accent);border-radius:2px">${{brand}} \u2014 ${{cat}}</div>`;
    html+=`<table style="width:100%;font-size:.7rem;border-collapse:collapse"><thead><tr style="background:var(--tbl-head)"><th style="width:32%;text-align:left;padding:4px 5px;color:#fff">Customer</th><th style="width:13%;text-align:right;padding:4px 5px;color:#fff">2025</th><th style="width:14%;text-align:right;padding:4px 5px;color:#fff">2026 Real</th><th style="width:11%;text-align:right;padding:4px 5px;color:#fff">vs 2025</th><th style="width:15%;text-align:right;padding:4px 5px;color:#fff">Share '25</th><th style="width:15%;text-align:right;padding:4px 5px;color:#fff">Share '26</th></tr></thead><tbody>`;
    rows.forEach(({{cu,v25,q25,v26,q26}})=>{{
      const d25=getV(v25,q25),d26=getV(v26,q26);
      html+=`<tr style="border-bottom:1px solid var(--border)"><td style="padding:3px 5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{cu}}">${{cu}}</td><td style="padding:3px 5px;text-align:right">${{fmtV(v25,q25)}}</td><td style="padding:3px 5px;text-align:right">${{fmtV(v26,q26)}}</td><td style="padding:3px 5px;text-align:right">${{pctPillSafe(d26,d25)}}</td><td style="padding:3px 5px;text-align:right">${{tot25>0?(d25/tot25*100).toFixed(1)+'%':'—'}}</td><td style="padding:3px 5px;text-align:right">${{tot26>0?(d26/tot26*100).toFixed(1)+'%':'—'}}</td></tr>`;
    }});
    html+='</tbody></table></div>';
  }});
  html+='</div></div>';
  return html;
}}

function mkTooltip(){{
  return {{callbacks:{{label:ctx=>' '+ctx.dataset.label+': '+fmtChartTooltip(ctx.raw)}}}};
}}

// ── Month filter ─────────────────────────────────────────────────────────────
function buildMonthButtons(){{
  const c=document.getElementById('monthBtns'); c.innerHTML='';
  MONTHS_EN.forEach((m,i)=>{{
    const b=document.createElement('button');
    b.className='mth-btn'+(selectedMonths.includes(i)?' active':'');
    b.textContent=m; b.onclick=()=>toggleMonth(i,b);
    c.appendChild(b);
  }});
}}
function toggleMonth(i,btn){{
  const idx=selectedMonths.indexOf(i);
  if(idx>=0){{selectedMonths.splice(idx,1);btn.classList.remove('active');}}
  else{{selectedMonths.push(i);selectedMonths.sort((a,b)=>a-b);btn.classList.add('active');}}
  updateAll();
}}
function selectAllMonths(){{ selectedMonths=[0,1,2,3,4,5,6,7,8,9,10,11]; buildMonthButtons(); updateAll(); }}
function clearAllMonths(){{ selectedMonths=[]; buildMonthButtons(); updateAll(); }}

// ── Theme ────────────────────────────────────────────────────────────────────
function toggleTheme(){{
  document.body.classList.toggle('light-mode');
  refreshColors();
  Object.keys(charts).forEach(id=>{{ if(charts[id]){{charts[id].destroy();charts[id]=null;}} }});
  Object.keys(tabDirty).forEach(t=>{{tabDirty[t]=true;}});
  if(currentTab==='overview') renderOverview();
  else switchTab(currentTab, document.querySelector('.tab-btn.active'));
}}

// ── Tabs ─────────────────────────────────────────────────────────────────────
function switchTab(tab, btn){{
  document.querySelectorAll('.tab-content').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el=>el.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  if(btn) btn.classList.add('active');
  currentTab=tab;
  if(tab==='overview') renderOverview();
  else if(tab==='historical'){{ if(tabDirty.historical) renderHistorical(); }}
  else if(tab==='channels'){{ if(tabDirty.channels) renderChannels(); }}
  else if(tab==='brands'){{ if(tabDirty.brands) renderBrands(); }}
  else if(tab==='family'){{ if(tabDirty.family) renderFamily(); }}
  else if(tab==='products'){{ if(tabDirty.products) renderProducts(); }}
  else if(tab==='customers'){{ if(tabDirty.customers) renderCustomers(); }}
  else if(tab==='salescust'){{ if(tabDirty.salescust) renderSalesByCu(); }}
  else if(tab==='custbrand'){{ if(tabDirty.custbrand) renderCustBrand(); }}
}}
function updateAll(){{
  renderKPIs();
  if(currentTab==='overview') renderOverview();
  else if(currentTab==='historical') updateHistorical();
  else if(currentTab==='channels') renderChannels();
  else if(currentTab==='brands') renderBrands();
  else if(currentTab==='family') renderFamily();
  else if(currentTab==='products') renderProducts();
  else if(currentTab==='customers') renderCustomers();
  else if(currentTab==='salescust') renderSalesByCu();
  else if(currentTab==='custbrand') renderCustBrand();
  Object.keys(tabDirty).forEach(t=>{{ if(t!==currentTab) tabDirty[t]=true; }});
  // Also re-mark current tab as dirty for future re-renders (viewMode change)
  tabDirty[currentTab]=false;
}}

// ── KPIs (header) ─────────────────────────────────────────────────────────────
function renderKPIs(){{
  const r26=sumReal(2026,selectedMonths), r25=sumReal(2025,selectedMonths), bp=sumBP(selectedMonths);
  const p25=safePct(r26,r25), pBP=safePct(r26,bp);
  function pc(p){{
    if(p==null)return`<span class="kpi-pct pct-neu">—</span>`;
    const cls=+p>=0?'pct-pos':'pct-neg';
    return `<span class="kpi-pct ${{cls}}">${{+p>=0?'+':''}}${{p}}%</span>`;
  }}
  document.getElementById('hdrKpis').innerHTML=`
    <div class="kpi-item"><div class="kpi-label">2026 Real</div><div class="kpi-val">${{fmtK(r26)}}</div></div>
    <div class="kpi-item"><div class="kpi-label">vs 2025</div><div class="kpi-val">${{fmtK(r25)}}</div>${{pc(p25)}}</div>
    <div class="kpi-item"><div class="kpi-label">vs BP</div><div class="kpi-val">${{fmtK(bp)}}</div>${{pc(pBP)}}</div>`;
}}

// ── OVERVIEW ─────────────────────────────────────────────────────────────────
function renderOverview(){{
  const r26=sumReal(2026,selectedMonths), r25=sumReal(2025,selectedMonths), bp=sumBP(selectedMonths);
  const p25=safePct(r26,r25), pBP=safePct(r26,bp);
  function heroPct(p){{
    if(p==null)return`<span class="hero-metric-pct neu">—</span>`;
    const cls=+p>=0?'pos':'neg';
    return`<span class="hero-metric-pct ${{cls}}">${{+p>=0?'+':''}}${{p}}%</span>`;
  }}

  const el=document.getElementById('overviewContent');
  // Hero card
  el.innerHTML=`
  <div class="hero-card">
    <div class="hero-flag">${{FLAG_URI?'<img src="'+FLAG_URI+'" width="52" height="39" style="border-radius:3px">':''}}</div>
    <div><div class="hero-name">${{COUNTRY}}</div><div class="hero-sub">${{selectedMonths.length===0?'2026':selectedMonths.length===12?'Full Year 2026':MONTHS_EN[selectedMonths[0]]+(selectedMonths.length>1?'-'+MONTHS_EN[selectedMonths[selectedMonths.length-1]]:'')+' 2026'}}</div></div>
    <div class="hero-metric"><div class="hero-metric-lbl">2026 Real</div><div class="hero-metric-val">${{fmt(r26)}}</div></div>
    <div class="hero-metric"><div class="hero-metric-lbl">vs 2025</div><div class="hero-metric-val">${{fmt(r25)}}</div>${{heroPct(p25)}}</div>
    <div class="hero-metric"><div class="hero-metric-lbl">vs BP 2026</div><div class="hero-metric-val">${{fmt(bp)}}</div>${{heroPct(pBP)}}</div>
  </div>
  <div class="row2 mb16">
    <div class="card"><div class="section-title"><i class="bi bi-bar-chart-line-fill"></i> Monthly Performance</div>
      <div class="chart-wrap" style="height:300px"><canvas id="chOvBar"></canvas></div></div>
    <div class="card"><div class="section-title"><i class="bi bi-pie-chart-fill"></i> Channel Mix 2026</div>
      <div class="chart-wrap" style="height:300px"><canvas id="chOvCh"></canvas></div></div>
  </div>
  <div class="row2 mb16">
    <div class="card"><div class="section-title"><i class="bi bi-tags-fill"></i> Brand Mix 2026</div>
      <div class="chart-wrap" style="height:280px"><canvas id="chOvB4"></canvas></div></div>
    <div class="card"><div class="section-title"><i class="bi bi-calculator-fill"></i> BP Attainment</div>
      <div id="bpAttCard" style="padding:10px 0"></div></div>
  </div>`;

  // Monthly bar chart (all months, highlighting selected)
  const selSet=new Set(selectedMonths);
  const vals25=MONTHS_EN.map((_,mi)=>getV(sumReal(2025,[mi]),sumRealQ(2025,[mi])));
  const vals26=MONTHS_EN.map((_,mi)=>getV(sumReal(2026,[mi]),sumRealQ(2026,[mi])));
  const valsBP=MONTHS_EN.map((_,mi)=>getV(sumBP([mi]),sumBPQ([mi])));
  destroyChart('chOvBar');
  charts.chOvBar=new Chart(document.getElementById('chOvBar'),{{
    type:'bar',
    data:{{labels:MONTHS_EN,datasets:[
      {{label:'2025',data:vals25,backgroundColor:MONTHS_EN.map((_,i)=>selSet.has(i)?'#3b82f699':'#3b82f633'),
        datalabels:{{display:ctx=>vals25[ctx.dataIndex]>10000,formatter:v=>fmtChartLbl(v),font:{{size:7}},color:'#93c5fd',anchor:'end',align:'top'}}}},
      {{label:'2026 Real',data:vals26,backgroundColor:MONTHS_EN.map((_,i)=>selSet.has(i)?'#f59e0bcc':'#f59e0b44'),
        datalabels:{{display:ctx=>vals26[ctx.dataIndex]>10000,formatter:v=>fmtChartLbl(v),font:{{size:8,weight:'700'}},color:'#fcd34d',anchor:'end',align:'top'}}}},
      {{label:'BP 2026',data:valsBP,backgroundColor:MONTHS_EN.map((_,i)=>selSet.has(i)?'#10b98166':'#10b98122'),
        datalabels:{{display:ctx=>valsBP[ctx.dataIndex]>10000,formatter:v=>fmtChartLbl(v),font:{{size:7}},color:'#6ee7b7',anchor:'end',align:'top'}}}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{labels:{{color:COLORS.text,font:{{size:11}}}}}},tooltip:mkTooltip(),datalabels:{{}}}},
      scales:{{
        x:{{ticks:{{color:COLORS.tick,font:{{size:10}}}},grid:{{color:COLORS.grid}}}},
        y:{{ticks:{{color:COLORS.tick,font:{{size:10}},callback:v=>fmtChartLbl(v)}},grid:{{color:COLORS.grid}}}}
      }}
    }}
  }});

  // Channel donut
  const chNames=Object.keys(CH_COLORS);
  const chVals=chNames.map(ch=>getV(sumDim(chReal,2026,selectedMonths,ch),sumDimQ(chRealQ,2026,selectedMonths,ch)));
  const chCols=chNames.map(ch=>CH_COLORS[ch]);
  const totCh=chVals.reduce((a,b)=>a+b,0);
  destroyChart('chOvCh');
  charts.chOvCh=new Chart(document.getElementById('chOvCh'),{{
    type:'doughnut',
    data:{{labels:chNames,datasets:[{{data:chVals,backgroundColor:chCols,borderWidth:2,borderColor:'var(--card)'}}]}},
    options:{{responsive:true,maintainAspectRatio:false,cutout:'55%',
      plugins:{{
        legend:{{position:'right',labels:{{color:COLORS.text,font:{{size:9}},padding:6,boxWidth:10,
          generateLabels:chart=>chart.data.labels.map((lbl,i)=>{{
            const v=chart.data.datasets[0].data[i];
            const pct=totCh>0?(v/totCh*100).toFixed(1):'0.0';
            return{{text:lbl+'  '+pct+'%',fillStyle:chCols[i],strokeStyle:chCols[i],fontColor:COLORS.text,hidden:false,index:i,datasetIndex:0}};
          }})
        }}}},
        tooltip:{{callbacks:{{label:ctx=>` ${{ctx.label}}: ${{fmtChartTooltip(ctx.raw)}} (${{totCh>0?(ctx.raw/totCh*100).toFixed(1):'0'}}%)`}}}},
        datalabels:{{display:ctx=>{{const t=ctx.dataset.data.reduce((a,b)=>a+b,0);return t>0&&ctx.dataset.data[ctx.dataIndex]/t>=0.10;}},
          formatter:(v,ctx)=>{{const t=ctx.dataset.data.reduce((a,b)=>a+b,0);return t>0?(v/t*100).toFixed(1)+'%':''}},
          color:'#fff',font:{{size:9,weight:'700'}}}}
      }}
    }}
  }});

  // Brand donut
  const b4Vals=BRAND4_ORDER.map(b=>getV(sumDim(b4Real,2026,selectedMonths,b),sumDimQ(b4RealQ,2026,selectedMonths,b)));
  const b4Cols=BRAND4_ORDER.map(b=>BRAND4_COLORS[b]);
  const totB4=b4Vals.reduce((a,b)=>a+b,0);
  destroyChart('chOvB4');
  charts.chOvB4=new Chart(document.getElementById('chOvB4'),{{
    type:'doughnut',
    data:{{labels:BRAND4_ORDER,datasets:[{{data:b4Vals,backgroundColor:b4Cols,borderWidth:2,borderColor:'var(--card)'}}]}},
    options:{{responsive:true,maintainAspectRatio:false,cutout:'55%',
      plugins:{{
        legend:{{position:'right',labels:{{color:COLORS.text,font:{{size:9}},padding:6,boxWidth:10,
          generateLabels:chart=>chart.data.labels.map((lbl,i)=>{{
            const v=chart.data.datasets[0].data[i];
            const pct=totB4>0?(v/totB4*100).toFixed(1):'0.0';
            return{{text:lbl+'  '+pct+'%',fillStyle:b4Cols[i],strokeStyle:b4Cols[i],fontColor:COLORS.text,hidden:false,index:i,datasetIndex:0}};
          }})
        }}}},
        tooltip:{{callbacks:{{label:ctx=>` ${{ctx.label}}: ${{fmtChartTooltip(ctx.raw)}} (${{totB4>0?(ctx.raw/totB4*100).toFixed(1):'0'}}%)`}}}},
        datalabels:{{display:ctx=>{{const t=ctx.dataset.data.reduce((a,b)=>a+b,0);return t>0&&ctx.dataset.data[ctx.dataIndex]/t>=0.08;}},
          formatter:(v,ctx)=>{{const t=ctx.dataset.data.reduce((a,b)=>a+b,0);return t>0?(v/t*100).toFixed(1)+'%':''}},
          color:'#fff',font:{{size:9,weight:'700'}}}}
      }}
    }}
  }});

  // BP attainment card
  const bpAtt=bp>0?(r26/bp*100).toFixed(1):null;
  const barW=bpAtt?Math.min(+bpAtt,100):0;
  const barCol=bpAtt&&+bpAtt>=100?'#10b981':bpAtt&&+bpAtt>=85?'#f59e0b':'#ef4444';
  const r24=sumReal(2024,selectedMonths);
  document.getElementById('bpAttCard').innerHTML=`
    <div style="margin-bottom:14px">
      <div style="font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px">BP Attainment</div>
      <div style="font-size:2rem;font-weight:800;color:${{barCol}}">${{bpAtt?bpAtt+'%':'—'}}</div>
      <div style="background:rgba(255,255,255,.08);border-radius:4px;height:7px;overflow:hidden;margin:6px 0">
        <div style="width:${{barW}}%;height:7px;border-radius:4px;background:${{barCol}};transition:width .4s"></div>
      </div>
      <div style="font-size:.75rem;color:var(--muted)">${{fmt(r26)}} of ${{fmt(bp)}}</div>
    </div>
    <div style="display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;justify-content:space-between;font-size:.8rem">
        <span style="color:var(--muted)">2024 (same period)</span>
        <span style="font-weight:600">${{fmt(r24)}}</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:.8rem">
        <span style="color:var(--muted)">Growth vs 2024</span>
        <span style="font-weight:600;color:${{+safePct(r26,r24)>=0?'var(--green)':'var(--red)'}}">${{safePct(r26,r24)!=null?safePct(r26,r24)+'%':'—'}}</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:.8rem">
        <span style="color:var(--muted)">Growth vs 2025</span>
        <span style="font-weight:600;color:${{+safePct(r26,r25)>=0?'var(--green)':'var(--red)'}}">${{safePct(r26,r25)!=null?safePct(r26,r25)+'%':'—'}}</span>
      </div>
    </div>`;
}}

// ── HISTORICAL ────────────────────────────────────────────────────────────────
function histLabels(){{ return [...YEARS_HIST.map(String),'2026 Real','BP 2026']; }}
function histRealVals(months){{
  const v=YEARS_HIST.map(y=>sumReal(y,months));
  v.push(sumReal(2026,months)); v.push(null); return v;
}}
function histBPVals(months){{
  const v=YEARS_HIST.map(()=>null); v.push(null); v.push(sumBP(months)); return v;
}}
function histSC2Vals(months){{
  const ptBg=YEARS_HIST.map(y=>sc2HasAdj(y)?'#f59e0b':'#8b5cf6');
  ptBg.push(sc2HasAdj(2026)?'#f59e0b':'#8b5cf6'); ptBg.push('#3b82f6');
  const v=YEARS_HIST.map(y=>sumSC2(y,months));
  v.push(sumSC2(2026,months)); v.push(sumBP(months)); return {{v,ptBg}};
}}

function lineCfg(labels,datasets){{
  return {{type:'line',data:{{labels,datasets}},options:{{
    responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:COLORS.text,font:{{size:11}}}}}},tooltip:mkTooltip(),
      datalabels:{{display:true,anchor:'end',align:'top',font:{{size:9}},
        formatter:v=>v&&Math.abs(v)>0?fmtK(v):null,
        color:ctx=>ctx.dataset.borderColor||'#e2e8f0'}}
    }},
    scales:{{
      x:{{ticks:{{color:COLORS.tick,font:{{size:10}}}},grid:{{color:COLORS.grid}}}},
      y:{{ticks:{{color:COLORS.tick,font:{{size:10}},callback:v=>fmtChartLbl(v)}},grid:{{color:COLORS.grid}}}}
    }}
  }}}};
}}

function histKpiHtml(v26,v25,vBP){{
  const p25=safePct(v26,v25),pBP=safePct(v26,vBP);
  const pc=p=>p==null?`<span class="hist-kpi-val neu">—</span>`
    :`<span class="hist-kpi-val ${{+p>=0?'pos':'neg'}}">${{+p>=0?'+':''}}${{p}}%</span>`;
  return`<div class="hist-kpis"><span class="hist-kpi-item"><span class="hist-kpi-lbl">vs 2025:</span>${{pc(p25)}}</span><span class="hist-kpi-item"><span class="hist-kpi-lbl">vs BP:</span>${{pc(pBP)}}</span></div>`;
}}

function renderSC2Table(){{
  const el=document.getElementById('sc2DetailHist');
  if(!el)return;
  const rows=[];
  [...YEARS_HIST,2026].forEach(yr=>{{
    const diff=(sc2Diff[String(yr)]||[]);
    const selDiff=diff.filter(mi=>selectedMonths.includes(mi));
    if(!selDiff.length)return;
    const rTot=selDiff.reduce((s,mi)=>s+((realM[yr]||{{}})[mi]||0),0);
    const sTot=selDiff.reduce((s,mi)=>s+(sc2M[yr]!=null&&sc2M[yr][mi]!=null?sc2M[yr][mi]:((realM[yr]||{{}})[mi]||0)),0);
    const d=sTot-rTot;
    rows.push(`<tr><td>${{yr}}</td><td style="text-align:right">${{fmt(rTot)}}</td><td style="text-align:right">${{fmt(sTot)}}</td><td style="text-align:right;color:${{d>=0?'var(--green)':'var(--red)'}}">${{fmtSigned(Math.round(d))}}</td></tr>`);
  }});
  el.innerHTML=rows.length?`<div style="margin-top:8px"><table><thead><tr><th style="width:20%;text-align:left">Year</th><th style="width:27%;text-align:right">Real</th><th style="width:27%;text-align:right">Scenario 2</th><th style="width:26%;text-align:right">Delta</th></tr></thead><tbody>${{rows.join('')}}</tbody></table></div>`:'';
}}

function renderHistorical(){{
  const labels=histLabels();
  const el=document.getElementById('histContent');
  const hasSC2=Object.keys(sc2Diff).length>0;

  el.innerHTML=`
  <div class="card mb16">
    <div class="section-title"><i class="bi bi-graph-up-arrow"></i> Historical — Real vs BP</div>
    <div id="histKpi"></div>
    <div class="chart-wrap" style="height:300px"><canvas id="chHistReal"></canvas></div>
  </div>
  ${{hasSC2?`<div class="card mb16">
    <div class="section-title" style="color:#8b5cf6"><i class="bi bi-diagram-2-fill"></i> Scenario 2 — Effect: ${{EFFECT}}</div>
    <div class="chart-wrap" style="height:300px"><canvas id="chHistSC2"></canvas></div>
    <div class="sc2-legend"><span></span>Amber point = adjusted months in selection</div>
    <div class="sc2-detail" id="sc2DetailHist"></div>
  </div>`:''}}</div>`;

  destroyChart('chHistReal');
  charts.chHistReal=new Chart(document.getElementById('chHistReal'),lineCfg(labels,[
    {{label:'Real',data:histRealVals(selectedMonths),borderColor:'#f59e0b',fill:false,tension:.3,pointRadius:4,backgroundColor:'rgba(245,158,11,.1)'}},
    {{label:'BP 2026',data:histBPVals(selectedMonths),borderColor:'#3b82f6',borderDash:[5,5],tension:.3,pointRadius:4,backgroundColor:'transparent'}}
  ]));
  document.getElementById('histKpi').innerHTML=histKpiHtml(
    sumReal(2026,selectedMonths),sumReal(2025,selectedMonths),sumBP(selectedMonths));

  if(hasSC2){{
    const {{v,ptBg}}=histSC2Vals(selectedMonths);
    destroyChart('chHistSC2');
    charts.chHistSC2=new Chart(document.getElementById('chHistSC2'),lineCfg(labels,[
      {{label:'Real',data:histRealVals(selectedMonths),borderColor:'#f59e0b',fill:false,tension:.3,pointRadius:3}},
      {{label:'Scenario 2',data:v,borderColor:'#8b5cf6',fill:false,tension:.3,pointRadius:5,pointBackgroundColor:ptBg}},
      {{label:'BP 2026',data:histBPVals(selectedMonths),borderColor:'#3b82f6',borderDash:[5,5],tension:.3,pointRadius:4,backgroundColor:'transparent'}}
    ]));
    renderSC2Table();
  }}
  tabDirty.historical=false;
}}

function updateHistorical(){{
  if(!charts.chHistReal)return;
  const labels=histLabels();
  charts.chHistReal.data.datasets[0].data=histRealVals(selectedMonths);
  charts.chHistReal.data.datasets[1].data=histBPVals(selectedMonths);
  charts.chHistReal.update();
  document.getElementById('histKpi').innerHTML=histKpiHtml(
    sumReal(2026,selectedMonths),sumReal(2025,selectedMonths),sumBP(selectedMonths));
  if(charts.chHistSC2){{
    const {{v,ptBg}}=histSC2Vals(selectedMonths);
    charts.chHistSC2.data.datasets[0].data=histRealVals(selectedMonths);
    charts.chHistSC2.data.datasets[1].data=v;
    charts.chHistSC2.data.datasets[1].pointBackgroundColor=ptBg;
    charts.chHistSC2.data.datasets[2].data=histBPVals(selectedMonths);
    charts.chHistSC2.update();
    renderSC2Table();
  }}
}}

// ── DIM ANALYSIS (shared for channels / brands / family / customers) ──────────
function destroyChart(id){{ if(charts[id]){{charts[id].destroy();charts[id]=null;}} }}

function renderDimTab(containerId, chartId, realData, bpData, realDataQ, bpDataQ, dims, dimColors, title, nameLbl, colW){{
  const tot26=sumReal(2026,selectedMonths), tot25=sumReal(2025,selectedMonths);
  const totQ26=sumRealQ(2026,selectedMonths), totQ25=sumRealQ(2025,selectedMonths);
  // Build rows sorted by 2026 value desc
  let dimRows = dims.map(d=>{{
    const v24=sumDim(realData,2024,selectedMonths,d);
    const v25=sumDim(realData,2025,selectedMonths,d);
    const v26=sumDim(realData,2026,selectedMonths,d);
    const vBP=sumBPDim(bpData,selectedMonths,d);
    const q24=sumDimQ(realDataQ,2024,selectedMonths,d);
    const q25=sumDimQ(realDataQ,2025,selectedMonths,d);
    const q26=sumDimQ(realDataQ,2026,selectedMonths,d);
    const qBP=sumDimBPQf(bpDataQ,selectedMonths,d);
    return {{d,v24,v25,v26,vBP,q24,q25,q26,qBP}};
  }}).sort((a,b)=>{{
    if(b.d==='OTHERS') return -1; if(a.d==='OTHERS') return 1;
    return getV(b.v26,b.q26)-getV(a.v26,a.q26);
  }});
  const STD_HDR=`<tr><th style="width:${{colW}}%">${{nameLbl}}</th><th style="width:11%">2024</th><th style="width:12%">2025</th><th style="width:13%">2026 Real</th><th style="width:10%">vs 2025</th><th style="width:12%">BP 2026</th><th style="width:10%">vs BP</th><th style="width:11%">Share '25</th><th style="width:11%">Share '26</th></tr>`;
  let rows=''; let sum24=0,sum25=0,sum26=0,sumBP_=0,sumQ24=0,sumQ25=0,sumQ26=0,sumQBP=0;
  dimRows.forEach(({{d,v24,v25,v26,vBP,q24,q25,q26,qBP}})=>{{
    sum24+=v24;sum25+=v25;sum26+=v26;sumBP_+=vBP;
    sumQ24+=q24;sumQ25+=q25;sumQ26+=q26;sumQBP+=qBP;
    const d25v=getV(v25,q25),d26v=getV(v26,q26),dBPv=getV(vBP,qBP);
    const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
    const sh25=tref25>0?(d25v/tref25*100).toFixed(1)+'%':'—';
    const sh26=tref26>0?(d26v/tref26*100).toFixed(1)+'%':'—';
    rows+=`<tr><td>${{d}}</td><td>${{fmtV(v24,q24)}}</td><td>${{fmtV(v25,q25)}}</td><td>${{fmtV(v26,q26)}}</td><td>${{pctPillSafe(d26v,d25v)}}</td><td>${{fmtV(vBP,qBP)}}</td><td>${{pctPillSafeBP(d26v,dBPv)}}</td><td>${{sh25}}</td><td>${{sh26}}</td></tr>`;
  }});
  const td25=getV(sum25,sumQ25),td26=getV(sum26,sumQ26),tdBP=getV(sumBP_,sumQBP);
  rows+=`<tr class="total-row"><td>TOTAL</td><td>${{fmtV(sum24,sumQ24)}}</td><td>${{fmtV(sum25,sumQ25)}}</td><td>${{fmtV(sum26,sumQ26)}}</td><td>${{pctPillSafe(td26,td25)}}</td><td>${{fmtV(sumBP_,sumQBP)}}</td><td>${{pctPillSafeBP(td26,tdBP)}}</td><td>100%</td><td>100%</td></tr>`;

  const sortedDims=dimRows.map(x=>x.d);
  const vals25=dimRows.map(x=>getV(x.v25,x.q25));
  const vals26=dimRows.map(x=>getV(x.v26,x.q26));
  const valsBP=dimRows.map(x=>getV(x.vBP,x.qBP));

  document.getElementById(containerId).innerHTML=`
  <div class="card mb16">
    <div class="section-title">${{title}}</div>
    <div class="tbl-wrap"><table><thead>${{STD_HDR}}</thead><tbody>${{rows}}</tbody></table></div>
  </div>
  <div class="card">
    <div class="chart-wrap" style="height:300px"><canvas id="${{chartId}}"></canvas></div>
  </div>`;

  destroyChart(chartId);
  charts[chartId]=new Chart(document.getElementById(chartId),{{
    type:'bar',
    data:{{labels:sortedDims,datasets:[
      {{label:'2025',data:vals25,backgroundColor:'#3b82f699',datalabels:{{display:ctx=>vals25[ctx.dataIndex]>0,formatter:v=>fmtChartLbl(v),font:{{size:8}},color:'#93c5fd',anchor:'end',align:'top'}}}},
      {{label:'2026 Real',data:vals26,backgroundColor:'#f59e0bcc',datalabels:{{display:ctx=>vals26[ctx.dataIndex]>0,formatter:v=>fmtChartLbl(v),font:{{size:8,weight:'700'}},color:'#fcd34d',anchor:'end',align:'top'}}}},
      {{label:'BP 2026',data:valsBP,backgroundColor:'#10b98166',datalabels:{{display:ctx=>valsBP[ctx.dataIndex]>0,formatter:v=>fmtChartLbl(v),font:{{size:8}},color:'#6ee7b7',anchor:'end',align:'top'}}}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{labels:{{color:COLORS.text,font:{{size:11}}}}}},tooltip:mkTooltip(),datalabels:{{}}}},
      scales:{{
        x:{{ticks:{{color:COLORS.tick,font:{{size:10}}}},grid:{{color:COLORS.grid}}}},
        y:{{ticks:{{color:COLORS.tick,font:{{size:10}},callback:v=>fmtChartLbl(v)}},grid:{{color:COLORS.grid}}}}
      }}
    }}
  }});
}}

function renderChannels(){{ renderDimTab('chContent','chChBar',chReal,chBP,chRealQ,chBPQ,['DOMESTIC','RETAIL','ONLINE','OTHER'],CH_COLORS,'<i class="bi bi-shop"></i> Channel Analysis','Channel',20); tabDirty.channels=false; }}
function renderBrands(){{ renderDimTab('b4Content','chB4Bar',b4Real,b4BP,b4RealQ,b4BPQ,BRAND4_ORDER,BRAND4_COLORS,'<i class="bi bi-tags-fill"></i> Brand Analysis','Brand',24); tabDirty.brands=false; }}
function renderFamily(){{
  const allFams=[...new Set([...Object.values(famReal).flatMap(yr=>Object.values(yr).flatMap(m=>Object.keys(m)))])];
  const sorted=allFams.map(f=>([f,sumDim(famReal,2026,selectedMonths,f)])).sort((a,b)=>b[0]==='OTHERS'?-1:a[0]==='OTHERS'?1:b[1]-a[1]).map(x=>x[0]);
  renderDimTab('famContent','chFamBar',famReal,famBP,famRealQ,famBPQ,sorted,{{}}, '<i class="bi bi-grid-3x3-gap-fill"></i> Family Analysis','Family',22);
  tabDirty.family=false;
}}

// ── CUSTOMERS ────────────────────────────────────────────────────────────────
function sumExtraCu(year,months,cu){{ return months.reduce((s,mi)=>s+(((extraCuReal[year]||{{}})[mi]||{{}})[cu]||0),0); }}
function sumExtraCuQ(year,months,cu){{ return months.reduce((s,mi)=>s+(((extraCuRealQ[year]||{{}})[mi]||{{}})[cu]||0),0); }}
function renderCustomers(){{
  const tot25=sumReal(2025,selectedMonths)||1, tot26=sumReal(2026,selectedMonths)||1;
  const totQ25=sumRealQ(2025,selectedMonths)||1, totQ26=sumRealQ(2026,selectedMonths)||1;
  const dims=[...top10,'OTHERS'];
  const rows=dims.map(cu=>{{
    const v24=sumDim(cuReal,2024,selectedMonths,cu), q24=sumDimQ(cuRealQ,2024,selectedMonths,cu);
    const v25=sumDim(cuReal,2025,selectedMonths,cu), q25=sumDimQ(cuRealQ,2025,selectedMonths,cu);
    const v26=sumDim(cuReal,2026,selectedMonths,cu), q26=sumDimQ(cuRealQ,2026,selectedMonths,cu);
    const vBP=sumBPDim(cuBP,selectedMonths,cu),    qBP=sumDimBPQf(cuBPQ,selectedMonths,cu);
    const ch=cuChannelMap[cu]||'—';
    return {{cu,ch,v24,q24,v25,q25,v26,q26,vBP,qBP}};
  }}).sort((a,b)=>a.cu==='OTHERS'?1:b.cu==='OTHERS'?-1:getV(b.v26,b.q26)-getV(a.v26,a.q26));
  const HDR=`<tr><th style="width:20%">Customer</th><th style="width:9%">Channel</th><th style="width:10%">2024</th><th style="width:11%">2025</th><th style="width:11%">2026 Real</th><th style="width:9%">vs 2025</th><th style="width:10%">BP 2026</th><th style="width:9%">vs BP</th><th style="width:11%">Share '26</th></tr>`;
  let h='', t24=0,tQ24=0,t25=0,tQ25=0,t26=0,tQ26=0,tbp=0,tBPQ=0;
  // Named rows with BP projection
  rows.filter(r=>r.cu!=='OTHERS').forEach(({{cu,ch,v24,q24,v25,q25,v26,q26,vBP,qBP}})=>{{
    t24+=v24;tQ24+=q24;t25+=v25;tQ25+=q25;t26+=v26;tQ26+=q26;tbp+=vBP;tBPQ+=qBP;
    const d25=getV(v25,q25),d26=getV(v26,q26),dBP=getV(vBP,qBP);
    const tref26=viewMode==='qty'?totQ26:tot26;
    h+=`<tr><td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{cu}}">${{cu}}</td>`;
    h+=`<td style="font-size:.68rem;color:var(--muted)">${{ch}}</td>`;
    h+=`<td>${{fmtV(v24,q24)}}</td><td>${{fmtV(v25,q25)}}</td><td>${{fmtV(v26,q26)}}</td>`;
    h+=`<td>${{pctPillSafe(d26,d25,getV(v24,q24))}}</td><td>${{fmtV(vBP,qBP)}}</td><td>${{pctPillSafeBP(d26,dBP)}}</td>`;
    h+=`<td>${{tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}}</td></tr>`;
  }});
  // OTHERS aggregate row
  const othRow=rows.find(r=>r.cu==='OTHERS');
  if(othRow){{
    const {{v24,q24,v25,q25,v26,q26,vBP,qBP}}=othRow;
    t24+=v24;tQ24+=q24;t25+=v25;tQ25+=q25;t26+=v26;tQ26+=q26;tbp+=vBP;tBPQ+=qBP;
    const d25=getV(v25,q25),d26=getV(v26,q26),dBP=getV(vBP,qBP);
    const tref26=viewMode==='qty'?totQ26:tot26;
    h+=`<tr style="opacity:.7"><td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">OTHERS</td>`;
    h+=`<td style="font-size:.68rem;color:var(--muted)">—</td>`;
    h+=`<td>${{fmtV(v24,q24)}}</td><td>${{fmtV(v25,q25)}}</td><td>${{fmtV(v26,q26)}}</td>`;
    h+=`<td>${{pctPillSafe(d26,d25)}}</td><td>${{fmtV(vBP,qBP)}}</td><td>${{pctPillSafeBP(d26,dBP)}}</td>`;
    h+=`<td>${{tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}}</td></tr>`;
    // Sub-level: top sellers without BP projection (inside Others bucket)
    if(extraCuList&&extraCuList.length>0){{
      extraCuList.forEach(exCu=>{{
        const ev24=sumExtraCu(2024,selectedMonths,exCu), eq24=sumExtraCuQ(2024,selectedMonths,exCu);
        const ev25=sumExtraCu(2025,selectedMonths,exCu), eq25=sumExtraCuQ(2025,selectedMonths,exCu);
        const ev26=sumExtraCu(2026,selectedMonths,exCu), eq26=sumExtraCuQ(2026,selectedMonths,exCu);
        const ech=extraCuChannelMap[exCu]||'—';
        const ed25=getV(ev25,eq25), ed26=getV(ev26,eq26);
        const tref26=viewMode==='qty'?totQ26:tot26;
        h+=`<tr style="opacity:.65;background:rgba(255,255,255,0.02)">`;
        h+=`<td style="padding-left:22px;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.78rem" title="${{exCu}}"><span style="color:var(--muted);margin-right:4px">└</span>${{exCu}}</td>`;
        h+=`<td style="font-size:.65rem;color:var(--muted)">${{ech}}</td>`;
        h+=`<td>${{fmtV(ev24,eq24)}}</td><td>${{fmtV(ev25,eq25)}}</td><td>${{fmtV(ev26,eq26)}}</td>`;
        h+=`<td>${{pctPillSafe(ed26,ed25,getV(ev24,eq24))}}</td><td style="color:var(--muted);font-size:.72rem;text-align:center">—</td><td style="color:var(--muted);font-size:.72rem;text-align:center">—</td>`;
        h+=`<td>${{tref26>0?(ed26/tref26*100).toFixed(1)+'%':'—'}}</td></tr>`;
      }});
    }}
  }}
  const td25=getV(t25,tQ25),td26=getV(t26,tQ26);
  const realTotBP=sumBP(selectedMonths), realTotBPQ=sumBPQ(selectedMonths);
  const tdbp=getV(realTotBP,realTotBPQ);
  h+=`<tr class="total-row"><td>TOTAL</td><td></td><td>${{fmtV(t24,tQ24)}}</td><td>${{fmtV(t25,tQ25)}}</td><td>${{fmtV(t26,tQ26)}}</td><td>${{pctPillSafe(td26,td25)}}</td><td>${{fmtV(realTotBP,realTotBPQ)}}</td><td>${{pctPillSafeBP(td26,tdbp)}}</td><td>100%</td></tr>`;
  document.getElementById('cuContent').innerHTML=`
  <div class="card mb16"><div class="section-title"><i class="bi bi-people-fill"></i> Customer Analysis</div>
    <div class="tbl-wrap"><table><thead>${{HDR}}</thead><tbody>${{h}}</tbody></table></div>
  </div><div id="bccMtxCu"></div>`;
  const _bccEl=document.getElementById('bccMtxCu');
  if(_bccEl) _bccEl.innerHTML=buildBccMatrix();
  tabDirty.customers=false;
}}

// ── SALES / CUSTOMER ──────────────────────────────────────────────────────────
function sumAllCu(year,months,cu){{ return months.reduce((s,mi)=>s+(((allCuReal[year]||{{}})[mi]||{{}})[cu]||0),0); }}
function sumAllCuQ(year,months,cu){{ return months.reduce((s,mi)=>s+(((allCuRealQ[year]||{{}})[mi]||{{}})[cu]||0),0); }}
let salesCuRows=[], salesCuTotals={{T24:0,TQ24:0,T25:0,TQ25:0,T26:0,TQ26:0}};
function renderSalesByCu(){{
  const rows=allCuList.map(cu=>{{
    const v24=sumAllCu(2024,selectedMonths,cu), q24=sumAllCuQ(2024,selectedMonths,cu);
    const v25=sumAllCu(2025,selectedMonths,cu), q25=sumAllCuQ(2025,selectedMonths,cu);
    const v26=sumAllCu(2026,selectedMonths,cu), q26=sumAllCuQ(2026,selectedMonths,cu);
    const ch=allCuChannelMap[cu]||'—';
    return {{cu,ch,v24,q24,v25,q25,v26,q26}};
  }}).filter(r=>r.v24||r.v25||r.v26).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
  salesCuRows=rows;
  salesCuTotals={{
    T24:rows.reduce((s,r)=>s+r.v24,0), TQ24:rows.reduce((s,r)=>s+r.q24,0),
    T25:rows.reduce((s,r)=>s+r.v25,0), TQ25:rows.reduce((s,r)=>s+r.q25,0),
    T26:rows.reduce((s,r)=>s+r.v26,0), TQ26:rows.reduce((s,r)=>s+r.q26,0)
  }};
  const channels=[...new Set(rows.map(r=>r.ch).filter(c=>c&&c!=='—'))].sort();
  const chOpts=channels.map(c=>`<option value="${{c}}">${{c}}</option>`).join('');
  const inputStyle='background:var(--card);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:5px 10px;font-size:.78rem';
  document.getElementById('salesCustContent').innerHTML=`
  <div class="card"><div class="section-title"><i class="bi bi-table"></i> Sales by Customer — All Customers</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
      <input type="text" id="salesCuSearch" placeholder="Search customer..." oninput="renderSalesByCuTable()" style="${{inputStyle}};min-width:220px">
      <select id="salesCuChannel" onchange="renderSalesByCuTable()" style="${{inputStyle}}">
        <option value="">All Channels</option>${{chOpts}}
      </select>
      <span id="salesCuCount" style="font-size:.72rem;color:var(--muted);margin-left:auto"></span>
    </div>
    <div class="tbl-wrap" id="salesCuTbl"></div>
  </div>`;
  renderSalesByCuTable();
  tabDirty.salescust=false;
}}
function renderSalesByCuTable(){{
  const searchEl=document.getElementById('salesCuSearch'), chEl=document.getElementById('salesCuChannel');
  const search=(searchEl?searchEl.value:'').trim().toLowerCase();
  const chFilter=chEl?chEl.value:'';
  const rows=salesCuRows.filter(r=>(!search||r.cu.toLowerCase().includes(search))&&(!chFilter||r.ch===chFilter));
  const {{T24,TQ24,T25,TQ25,T26,TQ26}}=salesCuTotals;
  const tref25=viewMode==='qty'?TQ25||1:T25||1, tref26=viewMode==='qty'?TQ26||1:T26||1;
  const HDR=`<tr>
    <th style="width:19%;text-align:left">Customer</th>
    <th style="width:9%">Channel</th>
    <th style="width:9%">2024</th>
    <th style="width:9%">2025</th>
    <th style="width:9%">vs 2024</th>
    <th style="width:9%">2026 Real</th>
    <th style="width:9%">vs 2025</th>
    <th style="width:9%">Share '25</th>
    <th style="width:9%">Share '26</th>
  </tr>`;
  let h=`<table style="table-layout:fixed"><thead>${{HDR}}</thead><tbody>`;
  const dT24=getV(T24,TQ24), dT25=getV(T25,TQ25), dT26=getV(T26,TQ26);
  h+=`<tr class="total-row"><td>TOTAL</td><td></td><td>${{fmtV(T24,TQ24)}}</td><td>${{fmtV(T25,TQ25)}}</td><td>${{pctPillSafe(dT25,dT24)}}</td><td>${{fmtV(T26,TQ26)}}</td><td>${{pctPillSafe(dT26,dT25,dT24)}}</td><td>100%</td><td>100%</td></tr>`;
  if(rows.length===0){{
    h+=`<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:14px">No customers match the filters</td></tr>`;
  }}
  rows.forEach(({{cu,ch,v24,q24,v25,q25,v26,q26}})=>{{
    const d24=getV(v24,q24), d25=getV(v25,q25), d26=getV(v26,q26);
    const sh25=tref25>0?(d25/tref25*100).toFixed(1)+'%':'—';
    const sh26=tref26>0?(d26/tref26*100).toFixed(1)+'%':'—';
    h+=`<tr><td style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.78rem" title="${{cu}}">${{cu}}</td>`;
    h+=`<td style="font-size:.68rem;color:var(--muted)">${{ch}}</td>`;
    h+=`<td>${{fmtV(v24,q24)}}</td><td>${{fmtV(v25,q25)}}</td><td>${{pctPillSafe(d25,d24)}}</td>`;
    h+=`<td>${{fmtV(v26,q26)}}</td><td>${{pctPillSafe(d26,d25,d24)}}</td>`;
    h+=`<td>${{sh25}}</td><td>${{sh26}}</td></tr>`;
  }});
  h+='</tbody></table>';
  document.getElementById('salesCuTbl').innerHTML=h;
  const cnt=document.getElementById('salesCuCount');
  if(cnt) cnt.textContent=`Showing ${{rows.length}} of ${{salesCuRows.length}} customers`;
}}

// ── PRODUCTS (SKU Top 20 + Travel Blue Top 20) ────────────────────────────────
function buildSkuTable(skuList, isTB){{
  const tot25=sumReal(2025,selectedMonths)||1, tot26=sumReal(2026,selectedMonths)||1;
  const totQ25=sumRealQ(2025,selectedMonths)||1, totQ26=sumRealQ(2026,selectedMonths)||1;
  const rows=skuList.map(sku=>{{
    const v24=isTB?sumDim(skuRealTB,2024,selectedMonths,sku):selectedMonths.reduce((s,mi)=>s+(((skuReal[2024]||{{}})[mi]||{{}})[sku]||0),0);
    const q24=isTB?sumSkuTBQ(2024,selectedMonths,sku):sumSkuQ(2024,selectedMonths,sku);
    const v25=isTB?sumDim(skuRealTB,2025,selectedMonths,sku):selectedMonths.reduce((s,mi)=>s+(((skuReal[2025]||{{}})[mi]||{{}})[sku]||0),0);
    const q25=isTB?sumSkuTBQ(2025,selectedMonths,sku):sumSkuQ(2025,selectedMonths,sku);
    const v26=isTB?sumDim(skuRealTB,2026,selectedMonths,sku):selectedMonths.reduce((s,mi)=>s+(((skuReal[2026]||{{}})[mi]||{{}})[sku]||0),0);
    const q26=isTB?sumSkuTBQ(2026,selectedMonths,sku):sumSkuQ(2026,selectedMonths,sku);
    return {{sku,v24,q24,v25,q25,v26,q26}};
  }}).sort((a,b)=>getV(b.v26,b.q26)-getV(a.v26,a.q26));
  const T24=rows.reduce((s,r)=>s+r.v24,0), TQ24=rows.reduce((s,r)=>s+r.q24,0);
  const T25=rows.reduce((s,r)=>s+r.v25,0), TQ25=rows.reduce((s,r)=>s+r.q25,0);
  const T26=rows.reduce((s,r)=>s+r.v26,0), TQ26=rows.reduce((s,r)=>s+r.q26,0);
  const tref25=viewMode==='qty'?totQ25:tot25, tref26=viewMode==='qty'?totQ26:tot26;
  const HDR=`<tr><th style="width:22%">SKU</th><th style="width:12%">Brand</th><th style="width:13%">Category</th><th style="width:9%">2024</th><th style="width:9%">2025</th><th style="width:10%">2026 Real</th><th style="width:8%">vs 2025</th><th style="width:8%">Share '25</th><th style="width:9%">Share '26</th></tr>`;
  let h=`<table><thead>${{HDR}}</thead><tbody>`;
  const lbl=isTB?'TB TOP 20':'TOP 20';
  const topSh25=tref25>0?(getV(T25,TQ25)/tref25*100).toFixed(1)+'%':'—';
  const topSh26=tref26>0?(getV(T26,TQ26)/tref26*100).toFixed(1)+'%':'—';
  h+=`<tr class="total-row"><td colspan="3">${{lbl}} TOTAL</td><td>${{fmtV(T24,TQ24)}}</td><td>${{fmtV(T25,TQ25)}}</td><td>${{fmtV(T26,TQ26)}}</td><td>${{pctPillSafe(getV(T26,TQ26),getV(T25,TQ25))}}</td><td>${{topSh25}}</td><td>${{topSh26}}</td></tr>`;
  rows.forEach(({{sku,v24,q24,v25,q25,v26,q26}})=>{{
    const d25=getV(v25,q25),d26=getV(v26,q26);
    h+=`<tr><td style="font-size:.68rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{sku}}">${{sku}}</td>`;
    h+=`<td style="font-size:.68rem">${{skuBrdMap[sku]||'—'}}</td><td style="font-size:.68rem">${{skuCatMap[sku]||'—'}}</td>`;
    h+=`<td>${{fmtV(v24,q24)}}</td><td>${{fmtV(v25,q25)}}</td><td>${{fmtV(v26,q26)}}</td>`;
    h+=`<td>${{pctPillSafe(d26,d25,getV(v24,q24))}}</td>`;
    h+=`<td>${{tref25>0?(d25/tref25*100).toFixed(1)+'%':'—'}}</td>`;
    h+=`<td>${{d26>0&&tref26>0?(d26/tref26*100).toFixed(1)+'%':'—'}}</td></tr>`;
  }});
  return h+'</tbody></table>';
}}

function renderProducts(){{
  let html='';
  if(top20TB&&top20TB.length>0){{
    html+=`<div class="card mb16"><div class="section-title" style="color:#3b82f6"><i class="bi bi-star-fill"></i> Top 20 SKUs — Travel Blue Brand Only</div><div class="tbl-wrap">${{buildSkuTable(top20TB,true)}}</div></div>`;
  }}
  html+=`<div class="card"><div class="section-title"><i class="bi bi-upc-scan"></i> Top 20 SKUs — All Brands</div><div class="tbl-wrap">${{buildSkuTable(top20,false)}}</div></div>`;
  document.getElementById('skuContent').innerHTML=html;
  tabDirty.products=false;
}}

// ── PDF EXPORT ───────────────────────────────────────────────────────────────
function exportPDF(){{
  const btn=document.getElementById('pdfBtn');
  btn.innerHTML='<i class="bi bi-hourglass-split"></i> Generating...';
  btn.disabled=true;
  html2canvas(document.body,{{
    scale:1.5, useCORS:true, allowTaint:true, logging:false,
    backgroundColor:'#0a0e1a',
    scrollX:0, scrollY:0,
    windowWidth:document.documentElement.scrollWidth,
    windowHeight:document.documentElement.scrollHeight
  }}).then(canvas=>{{
    const {{jsPDF}}=window.jspdf;
    const imgData=canvas.toDataURL('image/jpeg',0.92);
    const pdf=new jsPDF({{orientation:'landscape',unit:'mm',format:'a4'}});
    const pageW=pdf.internal.pageSize.getWidth();
    const pageH=pdf.internal.pageSize.getHeight();
    const imgH=(canvas.height*pageW)/canvas.width;
    let remaining=imgH, yPos=0;
    pdf.addImage(imgData,'JPEG',0,yPos,pageW,imgH);
    remaining-=pageH;
    while(remaining>0){{
      yPos-=pageH; pdf.addPage();
      pdf.addImage(imgData,'JPEG',0,yPos,pageW,imgH);
      remaining-=pageH;
    }}
    const tabName=document.querySelector('.tab-btn.active')?.textContent?.trim()||'dashboard';
    pdf.save(`{country}_${{tabName.replace(/\\s+/g,'_')}}_2026.pdf`);
    btn.innerHTML='<i class="bi bi-file-earmark-pdf"></i> Export PDF';
    btn.disabled=false;
  }}).catch(err=>{{
    console.error(err);
    btn.innerHTML='<i class="bi bi-file-earmark-pdf"></i> Export PDF';
    btn.disabled=false;
  }});
}}

// ── EXPORT EXCEL ─────────────────────────────────────────────────────────────
function exportExcel() {{
  const TAB_LABELS = {{
    'tab-overview':'Overview','tab-historical':'Historical',
    'tab-channels':'Channels','tab-brands':'Brands',
    'tab-family':'Family','tab-products':'Products',
    'tab-customers':'Customers','tab-salescust':'Sales x Cust',
    'tab-custbrand':'Cust x Brand'
  }};
  const wb = XLSX.utils.book_new();
  let sheetCount = 0;
  document.querySelectorAll('.tab-content').forEach(panel => {{
    const label = TAB_LABELS[panel.id] || panel.id.replace('tab-','');
    panel.querySelectorAll('table').forEach((tbl, i) => {{
      const tbls = panel.querySelectorAll('table');
      const name = (tbls.length > 1 ? label.slice(0,27) + '_' + (i+1) : label).slice(0,31);
      XLSX.utils.book_append_sheet(wb, XLSX.utils.table_to_sheet(tbl), name);
      sheetCount++;
    }});
  }});
  if (!sheetCount) {{ alert('No tables found.'); return; }}
  const title = document.title.replace(/[^a-z0-9]/gi,'_').replace(/_+/g,'_');
  XLSX.writeFile(wb, title + '.xlsx');
}}

// ── INIT ─────────────────────────────────────────────────────────────────────
refreshColors();
buildMonthButtons();
renderKPIs();
renderOverview();
</script>
</body>
</html>"""
    return html

# ── Main ──────────────────────────────────────────────────────────────────────
COUNTRY_LABEL = {'BRAZIL': 'Brasil', 'MEXICO': 'Mexico'}
for country in TARGET:
    print(f"\nBuilding {country}…")
    d    = build_data(country)
    html = generate_html(country, d)
    label = COUNTRY_LABEL.get(country, country.capitalize())
    out  = Path(r"C:\Users\Soporte\OneDrive - Travel Blue\Ambiente de Trabalho\Dashboards Camila\DASHBOARDS CAMINHO NOVO") / f"Business Review {label} 2026.html"
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  -> {out.name}  ({len(html)//1024} KB)")
    # Also write to original folder
    out2 = BASE_DIR / f"Business Review {label} 2026.html"
    with open(out2, 'w', encoding='utf-8') as f:
        f.write(html)

print("\nDone!")
