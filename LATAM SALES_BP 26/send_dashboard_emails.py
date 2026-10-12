"""
Send Travel Blue Business Review emails (one per market) via local Outlook.
No password needed — uses the Outlook session already open on your PC.

Usage:
    python send_dashboard_emails.py            # interactive (preview + confirm)
    python send_dashboard_emails.py --dry-run  # preview only, no send
"""

import os, sys, argparse, tempfile, webbrowser
import pandas as pd

# ── Configuration ──────────────────────────────────────────────────────────────

PERIOD     = "Enero-Septiembre 2026"
PERIOD_SHORT = "Ene–Set 2026"

HERE = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.normpath(os.path.join(HERE, r"..\..\DASHBOARDS CAMINHO NOVO"))
ANALISE = os.path.join(HERE, "ANALISE Q1 2026 2.xlsx")
BP_FILE = os.path.join(HERE, r"..\00.2026 - Latam.Sales.xlsx")

DASHBOARDS = [
    {
        "market": "LATAM",
        "file":   "Business Review LATAM 2026.html",
        "countries": ["MEXICO","BRAZIL","ARGENTINA","COLOMBIA","PANAMA","CHILE","PERU"],
        "recipients": [
            "guillermo@travel-blue.com",
            "soporte.latam@travel-blue.com",
            "pablo@travel-blue.com",
            "edgardo@travel-blue.com",
        ],
    },
    {
        "market": "Brasil",
        "file":   "Business Review Brasil 2026.html",
        "countries": ["BRAZIL"],
        "recipients": [
            "soporte.latam@travel-blue.com",
            "guillermo@travel-blue.com",
            "itamar@travel-blue.com",
            "pablo@travel-blue.com",
            "edgardo@travel-blue.com",
        ],
    },
    {
        "market": "México",
        "file":   "Business Review Mexico 2026.html",
        "countries": ["MEXICO"],
        "recipients": [
            "soporte.latam@travel-blue.com",
            "guillermo@travel-blue.com",
            "noe@travel-blue.com",
            "javo@travel-blue.com",
            "pablo@travel-blue.com",
            "edgardo@travel-blue.com",
        ],
    },
]

# ── Load data from ANALISE ─────────────────────────────────────────────────────

def load_kpis():
    """Read ANALISE and return per-country KPI dict for Jan-Jul 2026."""
    print("  Cargando datos de ANALISE para resumen...")
    df = pd.read_excel(ANALISE, sheet_name='SALES_SYSTEM_DATABASE', dtype=str)
    df['NET AMOUNT (USD)'] = pd.to_numeric(df['NET AMOUNT (USD)'], errors='coerce').fillna(0)
    df['YEAR']  = pd.to_numeric(df['YEAR'],  errors='coerce')
    months_ytd  = ['jan','fev','mar','abr','mai','jun','jul','ago','set']

    real26 = df[(df['YEAR']==2026) & (df['MONTH'].str.strip().isin(months_ytd)) & (df['TYPE']=='REAL')]
    real25 = df[(df['YEAR']==2025) & (df['MONTH'].str.strip().isin(months_ytd)) & (df['TYPE']=='REAL')]
    bp26   = df[(df['YEAR']==2026) & (df['MONTH'].str.strip().isin(months_ytd)) & (df['TYPE']=='BP 26')]

    kpis = {}
    all_countries = ["MEXICO","BRAZIL","ARGENTINA","COLOMBIA","PANAMA","CHILE","PERU"]
    for c in all_countries:
        r26 = real26[real26['COUNTRY']==c]['NET AMOUNT (USD)'].sum()
        r25 = real25[real25['COUNTRY']==c]['NET AMOUNT (USD)'].sum()
        bp  = bp26[bp26['COUNTRY']==c]['NET AMOUNT (USD)'].sum()
        vs_bp  = (r26/bp  - 1)*100 if bp  else 0
        vs_25  = (r26/r25 - 1)*100 if r25 else 0
        # Top 3 customers
        top3 = (real26[real26['COUNTRY']==c]
                .groupby('CUSTOMER 3')['NET AMOUNT (USD)'].sum()
                .sort_values(ascending=False)
                .head(3))
        top3 = [(k, v) for k, v in top3.items() if k not in ('OTHERS','nan','')]
        kpis[c] = {'r26': r26, 'r25': r25, 'bp': bp, 'vs_bp': vs_bp, 'vs_25': vs_25, 'top3': top3}

    # LATAM totals
    r26_lat = real26['NET AMOUNT (USD)'].sum()
    r25_lat = real25['NET AMOUNT (USD)'].sum()
    bp_lat  = bp26['NET AMOUNT (USD)'].sum()
    kpis['LATAM'] = {
        'r26': r26_lat, 'r25': r25_lat, 'bp': bp_lat,
        'vs_bp': (r26_lat/bp_lat -1)*100 if bp_lat else 0,
        'vs_25': (r26_lat/r25_lat-1)*100 if r25_lat else 0,
        'top3': []
    }
    return kpis

def fmt_usd(v):
    if v >= 1_000_000: return f"${v/1_000_000:.1f}M"
    return f"${v/1_000:.0f}K"

def pct_color(p):
    return "#15803d" if p >= 0 else "#b91c1c"

def pct_arrow(p):
    return "▲" if p >= 0 else "▼"

# ── Build email body ──────────────────────────────────────────────────────────

def build_body(cfg: dict, kpis: dict) -> str:
    market    = cfg["market"]
    filename  = cfg["file"]
    countries = cfg["countries"]

    # Aggregate KPIs for this market
    if market == "LATAM":
        k = kpis["LATAM"]
        # Per-country rows for LATAM
        country_rows = ""
        country_name_map = {
            "MEXICO":"México","BRAZIL":"Brasil","ARGENTINA":"Argentina",
            "COLOMBIA":"Colombia","PANAMA":"Panamá","CHILE":"Chile","PERU":"Perú"
        }
        for c in ["MEXICO","BRAZIL","ARGENTINA","COLOMBIA","PANAMA","CHILE","PERU"]:
            ck = kpis.get(c, {})
            r26 = ck.get('r26', 0); vs_bp = ck.get('vs_bp', 0); vs_25 = ck.get('vs_25', 0)
            bp_col  = pct_color(vs_bp); bp_arr = pct_arrow(vs_bp)
            y25_col = pct_color(vs_25); y25_arr = pct_arrow(vs_25)
            country_rows += f"""
            <tr style="border-top:1px solid #e2e8f0">
              <td style="padding:8px 12px;font-size:13px;font-weight:600;color:#1e293b">{country_name_map[c]}</td>
              <td style="padding:8px 12px;font-size:13px;text-align:right;color:#1e293b">{fmt_usd(r26)}</td>
              <td style="padding:8px 12px;font-size:13px;text-align:right;color:{bp_col};font-weight:600">{bp_arr}{abs(vs_bp):.1f}%</td>
              <td style="padding:8px 12px;font-size:13px;text-align:right;color:{y25_col};font-weight:600">{y25_arr}{abs(vs_25):.1f}%</td>
            </tr>"""

        summary_block = f"""
        <table style="width:100%;border-collapse:collapse;margin-top:16px;border:1px solid #e2e8f0;border-radius:6px;overflow:hidden">
          <thead>
            <tr style="background:#f8fafc">
              <th style="padding:8px 12px;font-size:12px;text-align:left;color:#64748b;font-weight:600">País</th>
              <th style="padding:8px 12px;font-size:12px;text-align:right;color:#64748b;font-weight:600">Real Ene–Set</th>
              <th style="padding:8px 12px;font-size:12px;text-align:right;color:#64748b;font-weight:600">vs BP</th>
              <th style="padding:8px 12px;font-size:12px;text-align:right;color:#64748b;font-weight:600">vs 2025</th>
            </tr>
          </thead>
          <tbody>{country_rows}</tbody>
        </table>"""

    else:
        c = countries[0]
        k = kpis.get(c, {})
        top3 = k.get('top3', [])
        top3_html = ""
        if top3:
            top3_html = "<p style='color:#334155;font-size:13px;margin-top:12px'><strong>Top clientes (Real Ene–Set):</strong></p><ul style='color:#334155;font-size:13px;line-height:1.9;padding-left:20px;margin:4px 0 0'>"
            for cu, v in top3:
                top3_html += f"<li>{cu} — {fmt_usd(v)}</li>"
            top3_html += "</ul>"

        summary_block = f"""
        <table style="width:100%;border-collapse:collapse;margin-top:16px;border:1px solid #e2e8f0;border-radius:6px;overflow:hidden">
          <thead>
            <tr style="background:#f8fafc">
              <th style="padding:10px 16px;font-size:12px;text-align:left;color:#64748b;font-weight:600">Métrica</th>
              <th style="padding:10px 16px;font-size:12px;text-align:right;color:#64748b;font-weight:600">Valor</th>
            </tr>
          </thead>
          <tbody>
            <tr style="border-top:1px solid #e2e8f0">
              <td style="padding:9px 16px;font-size:13px;color:#334155">Real Enero–Septiembre 2026</td>
              <td style="padding:9px 16px;font-size:14px;font-weight:700;text-align:right;color:#1e293b">{fmt_usd(k.get('r26',0))}</td>
            </tr>
            <tr style="border-top:1px solid #e2e8f0;background:#f8fafc">
              <td style="padding:9px 16px;font-size:13px;color:#334155">Business Plan 2026 (Ene–Set)</td>
              <td style="padding:9px 16px;font-size:14px;font-weight:700;text-align:right;color:#1e293b">{fmt_usd(k.get('bp',0))}</td>
            </tr>
            <tr style="border-top:1px solid #e2e8f0">
              <td style="padding:9px 16px;font-size:13px;color:#334155">Cumplimiento vs BP</td>
              <td style="padding:9px 16px;font-size:14px;font-weight:700;text-align:right;color:{pct_color(k.get('vs_bp',0))}">{pct_arrow(k.get('vs_bp',0))}{abs(k.get('vs_bp',0)):.1f}%</td>
            </tr>
            <tr style="border-top:1px solid #e2e8f0;background:#f8fafc">
              <td style="padding:9px 16px;font-size:13px;color:#334155">Variación vs 2025</td>
              <td style="padding:9px 16px;font-size:14px;font-weight:700;text-align:right;color:{pct_color(k.get('vs_25',0))}">{pct_arrow(k.get('vs_25',0))}{abs(k.get('vs_25',0)):.1f}%</td>
            </tr>
          </tbody>
        </table>
        {top3_html}"""

    # LATAM hero metrics
    r26  = k.get('r26',0); bp = k.get('bp',0); r25 = k.get('r25',0)
    vs_bp = k.get('vs_bp',0); vs_25 = k.get('vs_25',0)

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#f1f5f9">
  <tr><td align="center" style="padding:30px 16px">
    <table width="620" cellpadding="0" cellspacing="0"
           style="background:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.10)">

      <!-- Header -->
      <tr>
        <td style="background:#0f172a;padding:22px 32px">
          <span style="color:#ffffff;font-size:18px;font-weight:bold">Travel Blue</span>
          <span style="color:#94a3b8;font-size:14px;margin-left:10px">Business Review {PERIOD_SHORT}</span>
        </td>
      </tr>

      <!-- Title -->
      <tr>
        <td style="padding:28px 32px 0">
          <p style="margin:0;font-size:22px;font-weight:bold;color:#0f172a">
            Business Review {market}
          </p>
          <p style="margin:6px 0 0;font-size:14px;color:#64748b">
            Análisis acumulado <strong>{PERIOD}</strong>
          </p>
        </td>
      </tr>

      <!-- Hero KPIs -->
      <tr>
        <td style="padding:20px 32px 0">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 18px;text-align:center;width:33%">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Real Ene–Set 2026</p>
                <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#0f172a">{fmt_usd(r26)}</p>
              </td>
              <td style="width:8px"></td>
              <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 18px;text-align:center;width:33%">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">vs Business Plan</p>
                <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:{pct_color(vs_bp)}">{pct_arrow(vs_bp)}{abs(vs_bp):.1f}%</p>
              </td>
              <td style="width:8px"></td>
              <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 18px;text-align:center;width:33%">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">vs 2025</p>
                <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:{pct_color(vs_25)}">{pct_arrow(vs_25)}{abs(vs_25):.1f}%</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- Body -->
      <tr>
        <td style="padding:20px 32px">
          <p style="color:#334155;font-size:14px;line-height:1.6">Estimados,</p>
          <p style="color:#334155;font-size:14px;line-height:1.6;margin-top:8px">
            Adjuntamos el <strong>Business Review {market}</strong> con el análisis acumulado
            de <strong>{PERIOD}</strong>, incluyendo ventas reales, comparativo vs Business Plan 2026
            y evolución mensual respecto a 2025.
          </p>

          {summary_block}

          <p style="color:#334155;font-size:14px;line-height:1.6;margin-top:20px">
            El archivo adjunto
            (<code style="background:#f1f5f9;padding:2px 5px;border-radius:3px;font-size:12px">{filename}</code>)
            es interactivo. Descárguenlo y ábralo en Chrome o Edge.
          </p>
        </td>
      </tr>

      <!-- Note -->
      <tr>
        <td style="padding:0 32px 24px">
          <table cellpadding="0" cellspacing="0"
                 style="background:#f0fdf4;border-left:4px solid #16a34a;border-radius:4px;width:100%">
            <tr><td style="padding:10px 14px;font-size:13px;color:#15803d">
              El reporte funciona sin conexión a internet y no requiere instalación.
            </td></tr>
          </table>
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0">
          <p style="margin:0;font-size:12px;color:#94a3b8">
            Camila Lima · Travel Blue LATAM · soporte.latam@travel-blue.com
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


# ── Preview page ───────────────────────────────────────────────────────────────

def build_preview_page(kpis: dict) -> str:
    tabs_html = ""; panels_html = ""
    for i, cfg in enumerate(DASHBOARDS):
        active_tab = "active" if i == 0 else ""
        display    = "block"  if i == 0 else "none"
        recipients = ", ".join(cfg["recipients"])
        subject    = f"📊 Business Review {cfg['market']} — {PERIOD_SHORT}"
        body       = build_body(cfg, kpis)
        tabs_html += f'<button class="tab {active_tab}" onclick="showTab({i})">{cfg["market"]}</button>'
        panels_html += f"""
        <div class="panel" id="panel{i}" style="display:{display}">
          <div class="meta">
            <div class="meta-row"><span class="label">De:</span> soporte.latam@travel-blue.com</div>
            <div class="meta-row"><span class="label">Para:</span> {recipients}</div>
            <div class="meta-row"><span class="label">Asunto:</span> {subject}</div>
            <div class="meta-row"><span class="label">Adjunto:</span> {cfg['file']}</div>
          </div>
          <iframe srcdoc="{body.replace(chr(34),'&quot;').replace(chr(10),' ')}"
                  style="width:100%;height:600px;border:none"></iframe>
        </div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Preview — Dashboard Emails</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Arial,sans-serif;background:#f1f5f9;color:#1e293b}}
  header{{background:#0f172a;color:#fff;padding:18px 32px;display:flex;align-items:center;gap:12px}}
  header h1{{font-size:16px;font-weight:600}} header span{{font-size:13px;color:#94a3b8}}
  .tabs{{display:flex;gap:4px;padding:20px 32px 0}}
  .tab{{padding:9px 22px;border:none;border-radius:8px 8px 0 0;background:#e2e8f0;color:#64748b;cursor:pointer;font-size:14px;font-weight:600}}
  .tab.active{{background:#fff;color:#0f172a}}
  .content{{background:#fff;margin:0 32px 32px;border-radius:0 8px 8px 8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
  .meta{{background:#f8fafc;border-bottom:1px solid #e2e8f0;padding:16px 24px}}
  .meta-row{{font-size:13px;line-height:2;color:#475569}}
  .label{{font-weight:600;color:#0f172a;display:inline-block;width:70px}}
  .notice{{margin:20px 32px 0;padding:12px 16px;background:#fef9c3;border-left:4px solid #eab308;border-radius:4px;font-size:13px;color:#713f12}}
</style></head><body>
<header><h1>Travel Blue — Email Preview</h1><span>Revise antes de enviar · {PERIOD}</span></header>
<div class="notice">Vista previa del email. Cierre esta ventana y vuelva al terminal para confirmar el envío.</div>
<div class="tabs">{tabs_html}</div>
<div class="content">{panels_html}</div>
<script>function showTab(i){{document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('active',i===j));document.querySelectorAll('.panel').forEach((p,j)=>p.style.display=i===j?'block':'none');}}</script>
</body></html>"""


# ── Send via Outlook ──────────────────────────────────────────────────────────

def send_emails(dry_run: bool = False, auto_send: bool = False):
    try:
        import win32com.client
    except ImportError:
        print("\n✗  pywin32 no instalado. Ejecute:  pip install pywin32")
        sys.exit(1)

    print()
    print(f"{'[DRY-RUN] ' if dry_run else ''}Travel Blue — Envío de Dashboards")
    print("=" * 48)
    print(f"Período: {PERIOD}")
    print()

    # Load KPIs
    kpis = load_kpis()
    for c in ["LATAM","MEXICO","BRAZIL"]:
        k = kpis.get(c,{})
        print(f"  {c:<10} Real={fmt_usd(k.get('r26',0))}  vs BP={k.get('vs_bp',0):+.1f}%  vs 2025={k.get('vs_25',0):+.1f}%")
    print()

    # List dashboards
    for cfg in DASHBOARDS:
        filepath = os.path.join(DASHBOARD_DIR, cfg["file"])
        size_kb  = int(os.path.getsize(filepath)/1024) if os.path.isfile(filepath) else 0
        status   = f"{size_kb} KB" if size_kb else "⚠ NO ENCONTRADO"
        print(f"  {cfg['market']:8}  →  {', '.join(cfg['recipients'])}")
        print(f"            {cfg['file']} ({status})")
    print()

    if dry_run:
        print("Dry-run completo — ningún email enviado.")
        return

    if not auto_send:
        # Preview offer
        prev = input("¿Ver preview del email en el navegador? (s/n): ").strip().lower()
        if prev == 's':
            html = build_preview_page(kpis)
            tmp  = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8", prefix="email_preview_")
            tmp.write(html); tmp.close()
            webbrowser.open(f"file:///{tmp.name.replace(os.sep,'/')}")
            input("\n  Cierre la ventana del navegador y presione Enter para continuar...\n")

        # Confirm
        confirm = input(f"¿Enviar los {len(DASHBOARDS)} emails? (s/n): ").strip().lower()
        if confirm != 's':
            print("Cancelado.")
            return

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
    except Exception as e:
        print(f"\n✗  No se pudo conectar a Outlook: {e}")
        sys.exit(1)

    print()
    for cfg in DASHBOARDS:
        filepath = os.path.join(DASHBOARD_DIR, cfg["file"])
        try:
            mail         = outlook.CreateItem(0)
            mail.To      = "; ".join(cfg["recipients"])
            mail.Subject = f"📊 Business Review {cfg['market']} — {PERIOD_SHORT}"
            mail.HTMLBody = build_body(cfg, kpis)
            if os.path.isfile(filepath):
                mail.Attachments.Add(filepath)
            else:
                print(f"  ⚠  {cfg['market']}: adjunto no encontrado, enviando sin adjunto")
            mail.Send()
            print(f"  ✓  {cfg['market']} enviado a {len(cfg['recipients'])} destinatarios")
        except Exception as e:
            print(f"  ✗  {cfg['market']} falló: {e}")

    print()
    print("¡Listo! Todos los emails enviados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--send", action="store_true", help="Enviar sin confirmación interactiva")
    args = parser.parse_args()
    send_emails(dry_run=args.dry_run, auto_send=args.send)
