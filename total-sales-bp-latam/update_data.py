#!/usr/bin/env python3
"""
update_data.py — Atualiza os dados do dashboard Total Sales BP LATAM
====================================================================
Uso:
    python update_data.py <arquivo.csv>

O script detecta automaticamente o tipo de dado no CSV, mostra um preview
das mudanças e pede confirmação antes de gravar.

Formatos de CSV aceitos
-----------------------
1. MONTHLY (dados mensais por país ou total LATAM):
   Colunas obrigatórias: dataset, country, year_type, jan, fev, mar, abr, mai, jun, jul, ago, set, out, nov, dez
   dataset    → "monthly_country" ou "monthly_latam"
   country    → ex: "MEXICO", "BRAZIL", "LATAM" (só para monthly_latam)
   year_type  → "2025", "bp26" ou "real26"

2. YEARLY (totais anuais por país):
   Colunas: dataset, country, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2026_bp
   dataset → "country_yearly" ou "latam_yearly"

3. CUSTOMERS (clientes por país):
   Colunas: dataset, country, customer, 2025, bp26, sh25, sh26

4. BRANDS (marcas por país):
   Colunas: dataset, country, brand, 2025, bp26

5. FAMILY (famílias de produto):
   Colunas: dataset, country, family, v25, v26   (country="LATAM" para latam)
   ou para family_latam: dataset, family, 2025, bp26, pct, sh25, sh26

6. TOP PRODUCTS:
   Colunas: dataset, country, cat, sku, val, sh

7. CHANNEL:
   Colunas: dataset, channel, 2025, bp26

Exemplos de linhas CSV:
   monthly_country,MEXICO,real26,425.4,0,0,0,0,0,0,0,0,0,0,0
   monthly_latam,LATAM,real26,766.7,0,0,0,0,0,0,0,0,0,0,0
   country_yearly,MEXICO,,,,,,,,,425.4,,
"""

import csv
import json
import os
import sys
import copy
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(SCRIPT_DIR, "data")
SALES_FILE   = os.path.join(DATA_DIR, "sales_data.json")
BACKUP_DIR   = os.path.join(DATA_DIR, "backups")

MONTHS = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
YEARS  = ['2018','2019','2020','2021','2022','2023','2024','2025','2026','2026_bp']


# ── Helpers ────────────────────────────────────────────────────────────────

def load_data():
    with open(SALES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_backup(data):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(BACKUP_DIR, f"sales_data_{ts}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path

def save_data(data):
    with open(SALES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fval(v):
    """Parse float, return None if empty/invalid."""
    try:
        v = str(v).strip()
        return float(v) if v and v not in ('-', '') else None
    except:
        return None

def color_diff(old, new):
    if old is None and new is not None:
        return f"\033[32m+{new}\033[0m"  # green = new
    if old is not None and new is None:
        return f"\033[31m(removed)\033[0m"  # red = removed
    if old == new:
        return f"{new} (sem mudança)"
    pct = ((new - old) / abs(old) * 100) if old else 0
    arrow = "↑" if new > old else "↓"
    col = "\033[32m" if new > old else "\033[31m"
    return f"{old} → {col}{new} ({arrow}{abs(pct):.1f}%)\033[0m"

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ── Parsers por tipo de dataset ────────────────────────────────────────────

def parse_monthly(rows, data):
    """Returns list of (path_description, old_value, new_value, setter_fn)"""
    changes = []
    for row in rows:
        ds      = row.get('dataset','').strip()
        country = row.get('country','').strip().upper()
        ytype   = row.get('year_type','').strip()

        if ds == 'monthly_latam':
            src = data['monthly_latam']
            if ytype not in src:
                src[ytype] = {m: 0 for m in MONTHS}
            for m in MONTHS:
                nv = fval(row.get(m))
                if nv is None:
                    continue
                ov = src[ytype].get(m)
                path = f"monthly_latam.{ytype}.{m}"
                # Capture for closure
                def make_setter(src_ref, ytype_ref, m_ref, nv_ref):
                    return lambda d: d['monthly_latam'][ytype_ref].__setitem__(m_ref, nv_ref)
                changes.append((path, ov, nv, make_setter(src, ytype, m, nv)))

        elif ds == 'monthly_country':
            if country not in data['monthly_country']:
                data['monthly_country'][country] = {}
            src = data['monthly_country'][country]
            if ytype not in src:
                src[ytype] = {m: 0 for m in MONTHS}
            for m in MONTHS:
                nv = fval(row.get(m))
                if nv is None:
                    continue
                ov = src[ytype].get(m)
                path = f"monthly_country.{country}.{ytype}.{m}"
                def make_setter(c_ref, yt_ref, m_ref, nv_ref):
                    return lambda d: d['monthly_country'][c_ref][yt_ref].__setitem__(m_ref, nv_ref)
                changes.append((path, ov, nv, make_setter(country, ytype, m, nv)))

    return changes


def parse_yearly(rows, data):
    changes = []
    for row in rows:
        ds      = row.get('dataset','').strip()
        country = row.get('country','').strip().upper()

        if ds == 'country_yearly':
            if country not in data['country_yearly']:
                data['country_yearly'][country] = {}
            for yr in YEARS:
                nv = fval(row.get(yr))
                if nv is None:
                    continue
                ov = data['country_yearly'][country].get(yr)
                path = f"country_yearly.{country}.{yr}"
                def make_setter(c_ref, y_ref, nv_ref):
                    return lambda d: d['country_yearly'][c_ref].__setitem__(y_ref, nv_ref)
                changes.append((path, ov, nv, make_setter(country, yr, nv)))

        elif ds == 'latam_yearly':
            for yr in YEARS:
                nv = fval(row.get(yr))
                if nv is None:
                    continue
                ov = data['latam_yearly'].get(yr)
                path = f"latam_yearly.{yr}"
                def make_setter(y_ref, nv_ref):
                    return lambda d: d['latam_yearly'].__setitem__(y_ref, nv_ref)
                changes.append((path, ov, nv, make_setter(yr, nv)))

    return changes


def parse_customers(rows, data):
    changes = []
    for row in rows:
        country  = row.get('country','').strip().upper()
        customer = row.get('customer','').strip()
        v25  = fval(row.get('2025'))
        vbp  = fval(row.get('bp26'))
        sh25 = fval(row.get('sh25'))
        sh26 = fval(row.get('sh26'))

        src = data['customers_by_country'].get(country, [])
        existing = next((x for x in src if x['customer'].upper() == customer.upper()), None)

        for field, nv in [('2025', v25), ('bp26', vbp), ('sh25', sh25), ('sh26', sh26)]:
            if nv is None:
                continue
            ov = existing.get(field) if existing else None
            path = f"customers_by_country.{country}.{customer}.{field}"
            def make_setter(c_ref, cust_ref, f_ref, nv_ref, ex_ref):
                def setter(d):
                    lst = d['customers_by_country'].setdefault(c_ref, [])
                    item = next((x for x in lst if x['customer'].upper() == cust_ref.upper()), None)
                    if item is None:
                        item = {'customer': cust_ref}
                        lst.append(item)
                    item[f_ref] = nv_ref
                return setter
            changes.append((path, ov, nv, make_setter(country, customer, field, nv, existing)))

    return changes


def parse_channel(rows, data):
    changes = []
    for row in rows:
        ch   = row.get('channel','').strip().upper()
        v25  = fval(row.get('2025'))
        vbp  = fval(row.get('bp26'))
        for field, nv in [('2025', v25), ('bp26', vbp)]:
            if nv is None:
                continue
            ov = data['channel'].get(ch, {}).get(field)
            path = f"channel.{ch}.{field}"
            def make_setter(c_ref, f_ref, nv_ref):
                def setter(d):
                    d['channel'].setdefault(c_ref, {})[f_ref] = nv_ref
                return setter
            changes.append((path, ov, nv, make_setter(ch, field, nv)))
    return changes


def detect_and_parse(csv_path, data):
    """Auto-detect dataset type from CSV columns and parse all rows."""
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("❌ CSV vazio.")
        return []

    cols = set(rows[0].keys())
    print(f"\n📋 Colunas detectadas: {', '.join(cols)}")
    print(f"📊 Total de linhas: {len(rows)}")

    all_changes = []
    ds_types = set(r.get('dataset','').strip() for r in rows)
    print(f"📂 Datasets: {ds_types}")

    for ds in ds_types:
        ds_rows = [r for r in rows if r.get('dataset','').strip() == ds]
        if ds in ('monthly_latam', 'monthly_country'):
            all_changes += parse_monthly(ds_rows, data)
        elif ds in ('country_yearly', 'latam_yearly'):
            all_changes += parse_yearly(ds_rows, data)
        elif ds in ('customers_by_country', 'customers_latam'):
            all_changes += parse_customers(ds_rows, data)
        elif ds == 'channel':
            all_changes += parse_channel(ds_rows, data)
        else:
            print(f"⚠️  Dataset '{ds}' não reconhecido — linha ignorada.")

    return all_changes


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"❌ Arquivo não encontrado: {csv_path}")
        sys.exit(1)

    section(f"Carregando: {os.path.basename(csv_path)}")
    data = load_data()
    data_preview = copy.deepcopy(data)

    changes = detect_and_parse(csv_path, data_preview)

    if not changes:
        print("\n⚠️  Nenhuma mudança detectada no CSV.")
        sys.exit(0)

    # ── Preview ────────────────────────────────────────────────────────────
    section(f"Preview das mudanças ({len(changes)} campos)")

    new_vals = [c for c in changes if c[1] != c[2] and c[1] is None]
    upd_vals = [c for c in changes if c[1] != c[2] and c[1] is not None]
    same_vals = [c for c in changes if c[1] == c[2]]

    print(f"\n  🟢 Novos valores:      {len(new_vals)}")
    print(f"  🟡 Atualizações:       {len(upd_vals)}")
    print(f"  ⚪ Sem mudança:        {len(same_vals)}")

    if new_vals:
        print(f"\n  --- NOVOS ---")
        for path, ov, nv, _ in new_vals[:20]:
            print(f"    {path}: {color_diff(ov, nv)}")
        if len(new_vals) > 20:
            print(f"    ... e mais {len(new_vals)-20} novos.")

    if upd_vals:
        print(f"\n  --- ATUALIZAÇÕES ---")
        for path, ov, nv, _ in upd_vals[:20]:
            print(f"    {path}: {color_diff(ov, nv)}")
        if len(upd_vals) > 20:
            print(f"    ... e mais {len(upd_vals)-20} atualizações.")

    if same_vals and len(same_vals) <= 5:
        print(f"\n  --- SEM MUDANÇA (já estão corretos) ---")
        for path, ov, nv, _ in same_vals:
            print(f"    {path}: {nv}")

    # ── Confirmação ────────────────────────────────────────────────────────
    section("Confirmação")
    print("\n  Deseja gravar essas mudanças no arquivo de dados?")
    print("  [s] Sim, gravar    [n] Cancelar    [b] Sim + fazer backup\n")

    resp = input("  Sua escolha: ").strip().lower()

    if resp == 'n':
        print("\n❌ Operação cancelada. Nenhum arquivo foi alterado.")
        sys.exit(0)

    if resp == 'b':
        bk = save_backup(data)
        print(f"\n💾 Backup salvo: {bk}")

    if resp in ('s', 'b'):
        # Apply changes to original data
        real_data = load_data()
        for path, ov, nv, setter in changes:
            if ov != nv:
                setter(real_data)
        save_data(real_data)
        print(f"\n✅ {len([c for c in changes if c[1] != c[2]])} campos atualizados em {SALES_FILE}")
        print(f"   Recarregue o dashboard no navegador para ver as mudanças.\n")
    else:
        print("\n⚠️  Resposta não reconhecida. Operação cancelada.")
        sys.exit(1)


if __name__ == '__main__':
    main()
