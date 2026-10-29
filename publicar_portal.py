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


COUNTRIES = ["latam", "brasil", "mexico", "argentina", "chile", "colombia", "panama", "peru"]


def closing_folders_sorted():
    """Pastas de fechamento, da mais recente para a mais antiga."""
    out = []
    for d in glob.glob(os.path.join(REPO, "Relatorios Fechamento", "*_20*")):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d).upper()
        year = re.search(r"20\d\d", name)
        meses = [p for p in name.split("_") if p in MONTHS]
        if not year or not meses:
            continue
        # AGO_SEP_2026 -> vale pelo ultimo mes citado
        out.append((int(year.group()), MONTHS.index(meses[-1]), d))
    return [d for _, _, d in sorted(out, reverse=True)]


def latest_country_reports():
    """Para cada pais, o relatorio do fechamento mais recente que ja exista.

    Um mes parcial e normal: enquanto nem todos os paises fecharam Setembro,
    cada um fica com o mes mais recente em que foi gerado, em vez de todos
    voltarem para o mes anterior.

    Procuramos por glob dentro da pasta porque o sufixo do ficheiro nem sempre
    e igual ao nome da pasta (pasta SEP_2026, ficheiro ..._SET_2026.html).
    """
    found = {}
    for d in closing_folders_sorted():
        for c in COUNTRIES:
            if c in found:
                continue
            cands = glob.glob(os.path.join(d, f"SALES_REPORT_{c.upper()}_*.html"))
            if cands:
                found[c] = max(cands, key=os.path.getmtime)
    return found


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
        "global-ventas/marketplace-europe.html": newest(os.path.join(DC, "UK", "marketplace_sales_europe_*.html")),
        "global-ventas/total.html":    newest(os.path.join(DC, "TOTAL",   "total_*.html")),
        "global-ventas/aspac.html":    newest(os.path.join(DC, "ASPAC",   "*pac_*20*.html")),
        "global-ventas/consumption.html": newest(os.path.join(AT, "TB Consumption Dashboard*.html")),
        "global-ventas/online.html":   os.path.join(DC, "ONLINE", "online_2026.html"),
        "global-ventas/memory-collections.html": os.path.join(DC, "MEMORY COLLECTIONS", "memory_collections_2026.html"),
        "fechamento-latam/forecast-anual.html": newest(os.path.join(REPO, "Relatorios Fechamento", "*", "FORECAST_ANUAL_*.html")),
        # Forecast de 2 meses: o nome muda a cada mes (FORECAST_SEP_OCT_2026...),
        # por isso pegamos sempre o mais recente que nao seja o anual.
        "fechamento-latam/forecast.html": newest_forecast(),
    }
    reports = latest_country_reports()
    for c, src in reports.items():
        m[f"fechamento-latam/{c}.html"] = src
    return m, reports


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
    mapping, reports = copy_sources()
    print("\nFechamento escolhido para cada pais:")
    for c in COUNTRIES:
        src = reports.get(c)
        origem = os.path.basename(os.path.dirname(src)) if src else "- (nao gerado)"
        print(f"   {c:10} {origem}")
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
