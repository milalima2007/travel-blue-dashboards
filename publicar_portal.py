"""
publicar_portal.py - atualiza as copias dos paineis usadas pelo Portal do Equipo
e publica no site (GitHub -> Vercel).

1. Copia a versao mais recente de cada painel que vive fora desta pasta
   (Avolta, Heinemann, Liverpool, regioes globais, fechamento LATAM...).
2. Publica SOMENTE os ficheiros que o portal usa (lidos do portal-equipe.html).
3. Recusa publicar qualquer ficheiro que contenha chaves secretas.

Rodar com dois cliques em "PUBLICAR PORTAL.bat".
"""
import glob, hashlib, os, re, shutil, subprocess, sys

REPO = os.path.dirname(os.path.abspath(__file__))
DC   = os.path.dirname(REPO)              # Dashboards Camila
AT   = os.path.dirname(DC)                # Ambiente de Trabalho
PORTAL = os.path.join(REPO, "portal-equipe.html")

MONTHS = ["JAN", "FEV", "FEB", "MAR", "ABR", "APR", "MAI", "MAY", "JUN", "JUL",
          "AGO", "AUG", "SEP", "SET", "OCT", "OUT", "NOV", "DEZ", "DIC", "DEC"]

# Nunca publicar ficheiros com estas marcas (chaves de administrador / tokens)
SECRET_MARKERS = [b"service_role", b"sb_secret_", b"ghp_", b"github_pat_"]


def newest(pattern):
    files = [f for f in glob.glob(pattern)
             if not os.path.basename(f).lower().startswith("email")
             and "backup" not in f.lower()]
    return max(files, key=os.path.getmtime) if files else None


def newest_forecast():
    """Forecast rolante de 2 meses - o nome muda todo mes (FORECAST_SEP_OCT_2026)."""
    files = [f for f in glob.glob(os.path.join(REPO, "Relatorios Fechamento", "*", "FORECAST_*.html"))
             if "ANUAL" not in os.path.basename(f).upper()]
    return max(files, key=os.path.getmtime) if files else None


def latest_closing_folder():
    folders = [d for d in glob.glob(os.path.join(REPO, "Relatorios Fechamento", "*_20*"))
               if glob.glob(os.path.join(d, "SALES_REPORT_LATAM_*.html"))]

    def key(d):
        name = os.path.basename(d).upper()
        m = name.split("_")[0]
        year = re.search(r"20\d\d", name)
        return (int(year.group()) if year else 0, MONTHS.index(m) if m in MONTHS else -1)

    return max(folders, key=key) if folders else None


def copy_sources():
    """copia no portal -> original mais recente."""
    m = {
        "avolta-sellout/avolta-sales-out-analysis.html": os.path.join(DC, "AVOLTA SELLOUT", "avolta-sales-out-analysis.html"),
        "avolta-sellout/avolta-emea-analysis.html":      os.path.join(DC, "AVOLTA SELLOUT", "avolta-emea-analysis.html"),
        "avolta-sellout/avolta-ame-cei-analysis.html":   os.path.join(DC, "AVOLTA SELLOUT", "avolta-ame-cei-analysis.html"),
        "avolta-sellout/avolta-mexico-analysis.html":    os.path.join(DC, "AVOLTA SELLOUT", "avolta-mexico-analysis.html"),
        "avolta-sellout/avolta-brazil-analysis.html":    os.path.join(DC, "AVOLTA SELLOUT", "avolta-brazil-analysis.html"),
        "heinemann/HEINEMANN_DASHBOARD.html":            os.path.join(DC, "HEINEMANN", "HEINEMANN_DASHBOARD.html"),
        "mercado-libre/mercado-libre.html":              os.path.join(DC, "MERCADO LIBRE", "MERCADO LIBRE METRICAS.html"),
        "shopgallery/shopgallery.html":                  newest(os.path.join(DC, "SHOPGALLERY", "*.html")),
        "liverpool/liverpool.html":                      os.path.join(REPO, "Cloe Sellout", "Liverpool.html"),
        "global-ventas/europe.html":   newest(os.path.join(DC, "EUROPE",  "europe_*20*.html")),
        "global-ventas/germany.html":  newest(os.path.join(DC, "GERMANY", "germany_*20*.html")),
        "global-ventas/india.html":    newest(os.path.join(DC, "INDIA",   "india_*20*.html")),
        "global-ventas/china.html":    newest(os.path.join(DC, "CHINA",   "china_*20*.html")),
        "global-ventas/poland.html":   newest(os.path.join(DC, "POLAND",  "poland_*20*.html")),
        "global-ventas/uk.html":       newest(os.path.join(DC, "UK",      "uk_*20*.html")),
        "global-ventas/total.html":    newest(os.path.join(DC, "TOTAL",   "total_*.html")),
        "global-ventas/aspac.html":    newest(os.path.join(DC, "ASPAC",   "aspac_*.html")),
        "global-ventas/consumption.html": newest(os.path.join(AT, "TB Consumption Dashboard*.html")),
        "fechamento-latam/forecast-anual.html": newest(os.path.join(REPO, "Relatorios Fechamento", "*", "FORECAST_ANUAL_*.html")),
        # Forecast de 2 meses: o nome muda a cada mes (FORECAST_SEP_OCT_2026...),
        # por isso pegamos sempre o mais recente que nao seja o anual.
        "fechamento-latam/forecast.html": newest_forecast(),
    }
    folder = latest_closing_folder()
    if folder:
        tag = os.path.basename(folder)
        for c in ["latam", "brasil", "mexico", "argentina", "chile", "colombia", "panama", "peru"]:
            m[f"fechamento-latam/{c}.html"] = os.path.join(folder, f"SALES_REPORT_{c.upper()}_{tag}.html")
    return m, folder


def md5(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def portal_files():
    """Todos os ficheiros locais linkados no portal + o proprio portal."""
    html = open(PORTAL, encoding="utf-8").read()
    links = re.findall(r"(?:href|h):'([^']+)'", html)
    local = {l for l in links if not l.startswith(("http", "#"))}
    return sorted(local | {"portal-equipe.html"})


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    return r


def main():
    print("=" * 60)
    print(" PUBLICAR PORTAL DEL EQUIPO")
    print("=" * 60)

    # 1. Atualizar copias
    mapping, folder = copy_sources()
    print(f"\nFechamento mais recente: {os.path.basename(folder) if folder else '-'}")
    print("\n1) Atualizando copias dos paineis:")
    updated = 0
    for copy, src in mapping.items():
        dst = os.path.join(REPO, copy)
        if not src or not os.path.exists(src):
            print(f"   [aviso] sem original para {copy}")
            continue
        if os.path.exists(dst) and md5(dst) == md5(src):
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        updated += 1
        print(f"   atualizado: {copy}  <-  {os.path.basename(src)}")
    if not updated:
        print("   todas as copias ja estavam em dia")

    # 2. Selecionar apenas ficheiros do portal que mudaram
    files = [f for f in portal_files() if os.path.exists(os.path.join(REPO, f))]
    missing = [f for f in portal_files() if not os.path.exists(os.path.join(REPO, f))]
    for f in missing:
        print(f"   [aviso] o portal aponta para um ficheiro que nao existe: {f}")

    changed = git("status", "--porcelain", "--", *files).stdout.splitlines()
    changed = [line[3:].strip().strip('"') for line in changed]
    if not changed:
        print("\n2) Nada novo para publicar. O portal ja esta atualizado.")
        return 0

    # 3. Verificacao de seguranca
    print("\n2) Verificando que nenhum ficheiro tem chaves secretas...")
    for f in changed:
        with open(os.path.join(REPO, f), "rb") as fh:
            data = fh.read()
        hit = [m.decode() for m in SECRET_MARKERS if m in data]
        if hit:
            print(f"\n   BLOQUEADO: {f} contem {', '.join(hit)}.")
            print("   Nada foi publicado. Fala com a Camila/Claude antes de continuar.")
            return 1
    print("   ok")

    # 4. Publicar
    print(f"\n3) Publicando {len(changed)} ficheiro(s):")
    for f in changed:
        print(f"   - {f}")
    git("add", "--", *changed)
    git("commit", "-m", "chore: atualizar paineis do portal")
    git("pull", "origin", "main", "--no-rebase", "--no-edit")
    git("push", "origin", "main")

    print("\nPublicado! O portal atualiza em cerca de 1 minuto.")
    print("No navegador, use Ctrl + Shift + R para ver a versao nova.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERRO: {e}")
        print("Nada garantido como publicado. Envie esta mensagem para o Claude.")
        sys.exit(1)
