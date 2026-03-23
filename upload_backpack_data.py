#!/usr/bin/env python3
"""
Atualizador de Dados – Travel Blue Backpack & Luggage Dashboard
Uso: python upload_backpack_data.py [arquivo.xlsx]

Fluxo:
  1. Lê aba DATABASE do Excel
  2. Apaga dados antigos no Supabase (project_slug = 'backpack-lugagge')
  3. Faz upload dos novos dados em lotes de 500 linhas
  4. Reconstrói viewer.html (python build_viewer.py)
  5. Copia para tb-dashboard e faz push ao GitHub Pages
  6. Abre viewer.html localmente para conferência
"""
import sys, os, json, subprocess
from datetime import datetime

# ── Dependências ─────────────────────────────────────────────────────────────
for pkg in ['pandas', 'openpyxl', 'requests']:
    try:
        __import__(pkg)
    except ImportError:
        print(f"  Instalando {pkg}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

import pandas as pd
import requests

# ── Configuração ─────────────────────────────────────────────────────────────
DIR          = os.path.dirname(os.path.abspath(__file__))
BL_DIR       = os.path.join(DIR, 'backpack-lugagge')
EXCEL_DEFAULT= os.path.join(BL_DIR, 'SALES ALL TB GROUP - BACKPACKS&LUGGAGE - TB BRAND.xlsx')
VIEWER_PY    = os.path.join(BL_DIR, 'build_viewer.py')
VIEWER_OUT   = os.path.join(BL_DIR, 'viewer.html')
GHPAGES_DIR  = r'C:\Users\Soporte\tb-dashboard'

SUPABASE_URL  = 'https://llzwjuqhhmugljtwnlgl.supabase.co'
SERVICE_KEY   = ('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
                 'eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsendqdXFoaG11Z2xqdHdubGdsIiwi'
                 'cm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTYyNTM0NSwiZXhwIjoyMDg3'
                 'MjAxMzQ1fQ.UvitzSaul79yAD-iTiFjYDdeNrQhx6KfjU0YGEdNPOc')
PROJECT_SLUG  = 'backpack-lugagge'
CHUNK         = 500   # rows per Supabase batch

HEADERS = {
    'apikey':        SERVICE_KEY,
    'Authorization': f'Bearer {SERVICE_KEY}',
    'Content-Type':  'application/json',
    'Prefer':        'return=minimal',
}

# ── Leitura do Excel ─────────────────────────────────────────────────────────
def read_excel(path):
    print(f"\n[1/5] Lendo Excel: {os.path.basename(path)} ...")
    xl  = pd.ExcelFile(path)
    sh  = xl.sheet_names[0]
    df  = pd.read_excel(xl, sheet_name=sh)
    print(f"      Aba '{sh}' — {len(df):,} linhas, {len(df.columns)} colunas")

    # Tipos
    num_cols = ['YEAR','MONTH','QUANTITY','NET AMOUNT (USD)','COST','COST USD',
                'CBM','TOTAL COST','TOTAL COST USD']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'DATE' in df.columns:
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce').dt.strftime('%Y-%m-%d')

    rows = []
    for rec in df.to_dict(orient='records'):
        clean = {}
        for k, v in rec.items():
            if v is None:
                clean[k] = None
            elif isinstance(v, float) and (v != v):
                clean[k] = None
            elif hasattr(v, 'item'):
                clean[k] = v.item()
            else:
                clean[k] = v
        rows.append(clean)

    tipos = {}
    for r in rows:
        t = str(r.get('TYPE',''))
        tipos[t] = tipos.get(t, 0) + 1
    print(f"      Tipos: {tipos}")
    return rows

# ── Apagar dados antigos ──────────────────────────────────────────────────────
def delete_old(session):
    print(f"\n[2/5] Apagando dados antigos ({PROJECT_SLUG}) ...")
    r = session.delete(
        f'{SUPABASE_URL}/rest/v1/project_data',
        params={'project_slug': f'eq.{PROJECT_SLUG}'}
    )
    if r.status_code not in (200, 204):
        raise RuntimeError(f"Falha ao apagar: HTTP {r.status_code} — {r.text[:200]}")
    print(f"      OK")

# ── Upload em lotes ───────────────────────────────────────────────────────────
def upload_rows(session, rows):
    total = len(rows)
    print(f"\n[3/5] Enviando {total:,} linhas ao Supabase ...")
    records = [
        {'project_slug': PROJECT_SLUG,
         'composite_key': str(i),
         'row_data': row}
        for i, row in enumerate(rows)
    ]
    for start in range(0, total, CHUNK):
        chunk = records[start:start + CHUNK]
        r = session.post(
            f'{SUPABASE_URL}/rest/v1/project_data',
            data=json.dumps(chunk, ensure_ascii=False, default=str),
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Falha no upload (lote {start}): HTTP {r.status_code} — {r.text[:300]}")
        done = min(start + CHUNK, total)
        pct  = done * 100 // total
        bar  = '#' * (pct // 5) + '-' * (20 - pct // 5)
        print(f"      [{bar}] {done:,}/{total:,} ({pct}%)", end='\r', flush=True)
    print(f"      {'#'*20} {total:,}/{total:,} (100%) -- concluido")

# ── Rebuild viewer.html ───────────────────────────────────────────────────────
def rebuild_viewer():
    print(f"\n[4/5] Reconstruindo viewer.html ...")
    if not os.path.exists(VIEWER_PY):
        print(f"      AVISO: build_viewer.py nao encontrado em {BL_DIR}")
        return
    r = subprocess.run([sys.executable, VIEWER_PY],
                       capture_output=True, text=True, cwd=BL_DIR)
    if r.returncode != 0:
        print(f"      AVISO: build_viewer.py retornou erro:\n{r.stderr[:300]}")
    else:
        size = os.path.getsize(VIEWER_OUT) / 1024
        print(f"      OK — viewer.html ({size:.0f} KB)")

# ── Push ao GitHub Pages ──────────────────────────────────────────────────────
def push_github():
    print(f"\n[5/5] Publicando no GitHub Pages ...")
    if not os.path.exists(GHPAGES_DIR):
        print(f"      AVISO: pasta tb-dashboard nao encontrada em {GHPAGES_DIR}")
        return
    import shutil
    shutil.copy(VIEWER_OUT, os.path.join(GHPAGES_DIR, 'index.html'))
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    result = subprocess.run(
        f'cd /d "{GHPAGES_DIR}" && git add index.html && '
        f'git commit -m "data: update backpack dashboard {ts}" && git push',
        shell=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"      AVISO: git push falhou:\n{result.stderr[:300]}")
    else:
        print(f"      OK — GitHub Pages atualizado")

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    excel = sys.argv[1] if len(sys.argv) > 1 else EXCEL_DEFAULT
    if not os.path.exists(excel):
        print(f"  ERRO: Arquivo nao encontrado:\n  {excel}")
        sys.exit(1)

    print("=" * 60)
    print("  Travel Blue – Atualizando Backpack & Luggage Dashboard")
    print("=" * 60)
    start_ts = datetime.now()

    rows = read_excel(excel)

    session = requests.Session()
    session.headers.update(HEADERS)

    delete_old(session)
    upload_rows(session, rows)
    rebuild_viewer()
    push_github()

    elapsed = (datetime.now() - start_ts).seconds
    print(f"\n{'='*60}")
    print(f"  Concluído em {elapsed}s — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  viewer.html:  {VIEWER_OUT}")
    print(f"  GitHub Pages: https://travel-blue-latam.github.io/tb-dashboard/")
    print(f"{'='*60}\n")

    # Abre viewer.html localmente para conferência
    print("  Abrindo dashboard para conferência...")
    os.startfile(VIEWER_OUT)

if __name__ == '__main__':
    main()
