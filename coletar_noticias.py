"""
coletar_noticias.py - recolhe manchetes e estudos do sector e grava em
noticias.json, que o Portal del Equipo mostra na aba Mercado.

Como funciona:
  - acumula: junta as novidades ao que ja existia (nao apaga tudo todo o dia)
  - noticias: guarda as do ultimo mes (JANELA_NOTICIAS dias)
  - estudos:  relatorios e analises ficam muito mais tempo (JANELA_ESTUDOS)
  - se uma fonte falhar, o que ja estava guardado e mantido

Corre todos os dias no GitHub (.github/workflows/noticias.yml).
Nao precisa de nada instalado alem do Python.
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

FONTES = [
    ("The Moodie Davitt Report", "https://moodiedavittreport.com/feed/"),
    ("TRBusiness",               "https://www.trbusiness.com/feed/"),
    ("DFNI",                     "https://www.dfnionline.com/feed/"),
    ("ACI World",                "https://aci.aero/feed/"),
    # ABEAR foi retirada: o feed dela esta parado ha mais de um ano.
    # Continua como atalho na aba Mercado.
]

# Buscas dedicadas a "Travel Blue" (o feed normal so traz os ultimos dias,
# e a marca aparece poucas vezes por mes)
FONTES_TB = [
    ("DFNI", 'https://www.dfnionline.com/?s=%22travel+blue%22&feed=rss2'),
]

JANELA_NOTICIAS   = 30    # dias que uma noticia fica no portal
JANELA_ESTUDOS    = 365   # dias que um estudo/relatorio fica
JANELA_TRAVELBLUE = 365   # mencoes a Travel Blue: guardar muito tempo

# Mencoes a Travel Blue vao para uma seccao propria
TRAVEL_BLUE = re.compile(r"travel\s*blue", re.I)
POR_FONTE       = 15     # quantas ler de cada vez em cada fonte
TIMEOUT         = 30

# Titulos com estas palavras entram em "Estudos e relatorios"
PALAVRAS_ESTUDO = re.compile(
    r"\b(report|reports|study|studies|research|survey|outlook|forecast|"
    r"insight|insights|whitepaper|white paper|analysis|data|statistics|"
    r"traffic|results|index|ranking|ranks|benchmark|trends|"
    r"informe|estudio|relatorio|relatório|pesquisa|balanço|balanco|"
    r"anuario|anuário|estatística|estatistica|dados|tendências|tendencias)\b", re.I)

CABECALHOS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "noticias.json")
AGORA = datetime.now(timezone.utc)


def limpar(txt):
    if not txt:
        return ""
    txt = re.sub(r"<[^>]+>", "", txt)
    for a, b in [("&amp;", "&"), ("&#038;", "&"), ("&quot;", '"'), ("&nbsp;", " "),
                 ("&#8217;", "’"), ("&#8216;", "‘"), ("&#8220;", "“"), ("&#8221;", "”"),
                 ("&#8211;", "–"), ("&#8212;", "—"), ("&lt;", "<"), ("&gt;", ">")]:
        txt = txt.replace(a, b)
    return re.sub(r"\s+", " ", txt).strip()


def quando(item):
    for tag in ("pubDate", "{http://purl.org/dc/elements/1.1/}date", "updated", "published"):
        el = item.find(tag)
        if el is None or not el.text:
            continue
        for fn in (parsedate_to_datetime,
                   lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))):
            try:
                d = fn(el.text.strip())
                return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def ler_fonte(nome, url):
    pedido = urllib.request.Request(url, headers=CABECALHOS)
    with urllib.request.urlopen(pedido, timeout=TIMEOUT) as r:
        bruto = r.read()

    # alguns sites mandam comentarios HTML antes do XML
    corte = bruto.find(b"<rss")
    if corte < 0:
        corte = bruto.find(b"<?xml")
    if corte > 0:
        bruto = bruto[corte:]

    raiz = ET.fromstring(bruto)
    itens = raiz.findall(".//item") or raiz.findall(".//{http://www.w3.org/2005/Atom}entry")

    saida = []
    for it in itens[:POR_FONTE]:
        tit = it.find("title")
        lnk = it.find("link")
        href = (lnk.text if lnk is not None and lnk.text else
                (lnk.get("href") if lnk is not None else None))
        if tit is None or not href:
            continue
        titulo = limpar(tit.text)[:180]
        if not titulo:
            continue

        # o corpo so serve para procurar mencoes a Travel Blue
        corpo = " ".join(limpar(el.text) for el in it
                         if el.text and el.tag.lower().endswith(("description", "encoded", "summary")))

        if TRAVEL_BLUE.search(titulo) or TRAVEL_BLUE.search(corpo):
            tipo = "travelblue"
        elif PALAVRAS_ESTUDO.search(titulo):
            tipo = "estudo"
        else:
            tipo = "noticia"

        d = quando(it)
        saida.append({
            "fonte":  nome,
            "titulo": titulo,
            "url":    href.strip(),
            "data":   (d or AGORA).isoformat(),
            "tipo":   tipo,
        })
    return saida


# ── IATA ────────────────────────────────────────────────────────────
# A IATA nao tem feed: lemos a pagina onde ela lista os relatorios.
IATA_PAGINA = "https://www.iata.org/en/publications/economics/"
IATA_LINK   = re.compile(
    r'href="(?:https://www\.iata\.org)?(/en/publications/economics/'
    r'(?:reports|chart-week)/[^"#?]+)"')
# fora: carga e temas ambientais (a Camila quer passageiros/mercado)
IATA_FORA = re.compile(r"(cargo|saf|sustainab|plastic|environment)", re.I)
MESES = ("january february march april may june july august september "
         "october november december").split()


def titulo_do_endereco(caminho):
    nome = caminho.rstrip("/").split("/")[-1].replace("-", " ")
    return nome[:1].upper() + nome[1:]


def data_do_endereco(caminho):
    """Tenta descobrir a data pelo proprio endereco (ex.: ...-august-2026)."""
    texto = caminho.lower()
    ano = re.search(r"(20\d\d)", texto)
    if not ano:
        return None
    mes = next((i + 1 for i, m in enumerate(MESES) if m in texto), None)
    if mes is None:
        tri = re.search(r"q([1-4])", texto)
        mes = {1: 3, 2: 6, 3: 9, 4: 12}[int(tri.group(1))] if tri else 1
    dia = re.search(r"-(\d{1,2})-(?:" + "|".join(MESES) + ")-", texto)
    return datetime(int(ano.group(1)), mes, int(dia.group(1)) if dia else 1,
                    tzinfo=timezone.utc)


def ler_iata():
    pedido = urllib.request.Request(IATA_PAGINA, headers=CABECALHOS)
    with urllib.request.urlopen(pedido, timeout=TIMEOUT) as r:
        html = r.read().decode("utf-8", "replace")

    saida, vistos = [], set()
    for caminho in IATA_LINK.findall(html):
        if caminho in vistos or IATA_FORA.search(caminho):
            continue
        vistos.add(caminho)
        d = data_do_endereco(caminho)
        saida.append({
            "fonte":  "IATA",
            "titulo": titulo_do_endereco(caminho)[:180],
            "url":    "https://www.iata.org" + caminho,
            "data":   (d or AGORA).isoformat(),
            "tipo":   "estudo",      # tudo o que a IATA lista aqui e relatorio
        })
    return saida


def carregar_anteriores():
    if not os.path.exists(SAIDA):
        return []
    try:
        with open(SAIDA, encoding="utf-8") as f:
            d = json.load(f)
        return (d.get("noticias") or []) + (d.get("estudos") or [])
    except Exception:
        return []


def dentro_da_janela(item):
    try:
        d = datetime.fromisoformat(item["data"])
    except Exception:
        return False
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    limite = {"estudo": JANELA_ESTUDOS,
              "travelblue": JANELA_TRAVELBLUE}.get(item.get("tipo"), JANELA_NOTICIAS)
    return d >= AGORA - timedelta(days=limite)


def main():
    antigos = carregar_anteriores()
    novos, problemas = [], []

    for nome, url in FONTES:
        try:
            itens = ler_fonte(nome, url)
            novos.extend(itens)
            print(f"{nome}: {len(itens)} itens")
        except Exception as e:
            problemas.append(nome)
            print(f"{nome}: FALHOU ({type(e).__name__}: {e})")

    for nome, url in FONTES_TB:
        try:
            itens = [i for i in ler_fonte(nome, url) if TRAVEL_BLUE.search(i["titulo"])]
            for i in itens:
                i["tipo"] = "travelblue"
            novos.extend(itens)
            print(f"{nome} (Travel Blue): {len(itens)} itens")
        except Exception as e:
            problemas.append(f"{nome}/TravelBlue")
            print(f"{nome} (Travel Blue): FALHOU ({type(e).__name__}: {e})")

    try:
        itens = ler_iata()
        novos.extend(itens)
        print(f"IATA: {len(itens)} relatorios")
    except Exception as e:
        problemas.append("IATA")
        print(f"IATA: FALHOU ({type(e).__name__}: {e})")

    if not novos and not antigos:
        print("Nenhuma fonte respondeu e nao havia nada guardado.")
        return 1

    # juntar, remover repetidos pelo endereco, cortar o que ja passou da janela
    por_url = {}
    for it in antigos + novos:          # os novos sobrepoem-se aos antigos
        if it.get("url"):
            por_url[it["url"]] = it

    vivos = [it for it in por_url.values() if dentro_da_janela(it)]
    vivos.sort(key=lambda n: n.get("data") or "", reverse=True)

    travelblue = [n for n in vivos if n.get("tipo") == "travelblue"]
    estudos    = [n for n in vivos if n.get("tipo") == "estudo"]
    noticias   = [n for n in vivos if n.get("tipo") not in ("estudo", "travelblue")]

    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump({
            "atualizado": AGORA.isoformat(timespec="seconds"),
            "janela_noticias_dias": JANELA_NOTICIAS,
            "janela_estudos_dias": JANELA_ESTUDOS,
            "fontes_com_falha": problemas,
            "travelblue": travelblue,
            "noticias": noticias,
            "estudos": estudos,
        }, f, ensure_ascii=False, indent=1)

    print(f"\nguardados: {len(noticias)} noticias (ultimos {JANELA_NOTICIAS} dias) "
          f"+ {len(estudos)} estudos + {len(travelblue)} sobre Travel Blue")
    if problemas:
        print("fontes com falha:", ", ".join(problemas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
