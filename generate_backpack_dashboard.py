#!/usr/bin/env python3
"""
Gerador de Dashboard Offline – Travel Blue Backpack & Luggage
Uso: python generate_backpack_dashboard.py [arquivo.xlsx] [saida.html]
  ou arraste o Excel sobre o arquivo .bat

Lê a aba DATABASE do Excel, incorpora os dados no viewer.html
e gera um HTML standalone que abre sem servidor nem internet.
"""
import sys, os, json
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("  ERRO: pandas nao instalado. Execute: pip install pandas openpyxl")
    sys.exit(1)

# ── Caminhos padrão ──────────────────────────────────────────────────────────
DIR          = os.path.dirname(os.path.abspath(__file__))
BL_DIR       = os.path.join(DIR, 'backpack-lugagge')
EXCEL_DEFAULT= os.path.join(BL_DIR, 'SALES ALL TB GROUP - BACKPACKS&LUGGAGE - TB BRAND.xlsx')
TEMPLATE     = os.path.join(BL_DIR, 'viewer.html')
OUTPUT       = os.path.join(BL_DIR, 'dashboard-local.html')

# Colunas mantidas (descarta colunas redundantes para reduzir tamanho)
KEEP_COLS = [
    'CUSTOMER GROUPED NAME', 'CUSTOMER BP',
    'COUNTRY', 'REGION', 'COUNTRY 2', 'COMPANY', 'CHANNEL',
    'DATE', 'YEAR', 'MONTH',
    'SKU 2', 'DESCRIPTION', 'FAMILY', 'CATEGORY', 'SUB-CATEGORY',
    'SIZE', 'COLOR',
    'QUANTITY', 'NET AMOUNT (USD)', 'TYPE',
    'COST', 'COST USD', 'CBM',
    'Status Global', 'Status Local',
]

# ── Leitura do Excel ─────────────────────────────────────────────────────────
def read_excel(path):
    print(f"  Lendo: {os.path.basename(path)} ...")
    xl  = pd.ExcelFile(path)
    sh  = xl.sheet_names[0]          # sempre aba DATABASE
    df  = pd.read_excel(xl, sheet_name=sh)
    print(f"  Aba '{sh}' — {len(df):,} linhas, {len(df.columns)} colunas")

    # Mantém somente colunas necessárias (ignorando as que não existirem)
    keep = [c for c in KEEP_COLS if c in df.columns]
    df   = df[keep]

    # Converte tipos para JSON-serializáveis
    num_cols = ['YEAR','MONTH','QUANTITY','NET AMOUNT (USD)','COST','COST USD','CBM']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'DATE' in df.columns:
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce').dt.strftime('%Y-%m-%d')

    # Converte NaN → None para JSON null
    rows = []
    for rec in df.to_dict(orient='records'):
        clean = {}
        for k, v in rec.items():
            if v is None:
                clean[k] = None
            elif isinstance(v, float) and (v != v):  # NaN check
                clean[k] = None
            elif hasattr(v, 'item'):                  # numpy scalar
                clean[k] = v.item()
            else:
                clean[k] = v
        rows.append(clean)

    print(f"  Tipos: { {t: sum(1 for r in rows if r.get('TYPE')==t) for t in set(r.get('TYPE','') for r in rows)} }")
    return rows

# ── Geração do HTML standalone ───────────────────────────────────────────────
def generate(excel_path, output_path):
    if not os.path.exists(excel_path):
        print(f"  ERRO: Arquivo nao encontrado: {excel_path}")
        sys.exit(1)
    if not os.path.exists(TEMPLATE):
        print(f"  ERRO: viewer.html nao encontrado: {TEMPLATE}")
        sys.exit(1)

    rows = read_excel(excel_path)

    print("  Serializando JSON ...")
    json_data = json.dumps(rows, ensure_ascii=False, separators=(',', ':'))

    print("  Lendo template ...")
    with open(TEMPLATE, encoding='utf-8') as f:
        html = f.read()

    # ── Marca de geração no <title> ──────────────────────────────────────────
    ts = datetime.now().strftime('%d/%m/%Y %H:%M')
    html = html.replace(
        '<title>Travel Blue | Backpack &amp; Luggage</title>',
        f'<title>Travel Blue | Backpack &amp; Luggage — {ts}</title>'
    )

    # ── Bloco de inicialização substituto (sem Supabase) ────────────────────
    ASYNC_START = '(async () => {'
    ASYNC_END   = '})();'

    start = html.rfind(ASYNC_START)
    end   = html.rfind(ASYNC_END)
    if start == -1 or end == -1:
        print("  ERRO: bloco de inicializacao nao encontrado em viewer.html")
        sys.exit(1)

    new_init = f"""
  // ── DADOS INCORPORADOS — gerado em {ts} ──────────────────────────────────
  (function() {{
    if (typeof lucide !== 'undefined') lucide.createIcons();
    document.getElementById('btn-theme')?.addEventListener('click', () => ThemeToggle.toggle());

    const rows = {json_data};

    resolveColumns(rows[0]);
    _all   = C.company ? rows.filter(r => !norm(r[C.company]).includes('interco')) : rows;
    console.log('[BL] embedded rows:', _all.length);
    _filt  = [..._all];
    document.getElementById('state-loading').style.display = 'none';
    document.getElementById('dash-wrap').style.display     = 'block';
    populateFilters();
    showTab('overview');
  }})();"""

    html = html[:start] + new_init + html[end + len(ASYNC_END):]

    print(f"  Escrevendo: {os.path.basename(output_path)} ...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  Tamanho: {size_mb:.1f} MB")
    print(f"  Concluido em {ts}")
    return output_path

# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    excel  = sys.argv[1] if len(sys.argv) > 1 else EXCEL_DEFAULT
    output = sys.argv[2] if len(sys.argv) > 2 else OUTPUT
    path   = generate(excel, output)
    print()
    print(f"  Abrindo dashboard ...")
    os.startfile(path)
