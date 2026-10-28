"""
coletar_noticias.py - recolhe as manchetes do sector e grava em noticias.json,
que o Portal del Equipo le na aba Mercado.

Corre todos os dias no GitHub (ver .github/workflows/noticias.yml).
Nao precisa de nada instalado alem do Python.
"""
import json, os, re, sys, urllib.request, urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

FONTES = [
    ("The Moodie Davitt Report", "https://moodiedavittreport.com/feed/"),
    ("TRBusiness",               "https://www.trbusiness.com/feed/"),
    ("DFNI",                     "https://www.dfnionline.com/feed/"),
    ("ABEAR",                    "https://www.abear.com.br/feed/"),
]

POR_FONTE = 6          # manchetes guardadas por fonte
TOTAL_MAX = 24         # teto geral
TIMEOUT   = 30

CABECALHOS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "noticias.json")


def limpar(txt):
    if not txt:
        return ""
    txt = re.sub(r"<[^>]+>", "", txt)                       # tira HTML
    txt = (txt.replace("&amp;", "&").replace("&#8217;", "’")
              .replace("&#8216;", "‘").replace("&quot;", '"')
              .replace("&#8220;", "“").replace("&#8221;", "”")
              .replace("&nbsp;", " ").replace("&#038;", "&"))
    return re.sub(r"\s+", " ", txt).strip()


def quando(item):
    for tag in ("pubDate", "{http://purl.org/dc/elements/1.1/}date"):
        el = item.find(tag)
        if el is None or not el.text:
            continue
        try:
            d = parsedate_to_datetime(el.text)
        except Exception:
            try:
                d = datetime.fromisoformat(el.text.replace("Z", "+00:00"))
            except Exception:
                continue
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    return None


def ler_fonte(nome, url):
    pedido = urllib.request.Request(url, headers=CABECALHOS)
    with urllib.request.urlopen(pedido, timeout=TIMEOUT) as r:
        bruto = r.read()

    raiz = ET.fromstring(bruto)
    itens = raiz.findall(".//item") or raiz.findall(".//{http://www.w3.org/2005/Atom}entry")

    saida = []
    for it in itens[:POR_FONTE]:
        titulo = it.find("title")
        link = it.find("link")
        href = (link.text if link is not None and link.text else
                (link.get("href") if link is not None else None))
        if titulo is None or not href:
            continue
        d = quando(it)
        saida.append({
            "fonte": nome,
            "titulo": limpar(titulo.text)[:180],
            "url": href.strip(),
            "data": d.isoformat() if d else None,
        })
    return saida


def main():
    noticias, problemas = [], []
    for nome, url in FONTES:
        try:
            itens = ler_fonte(nome, url)
            noticias.extend(itens)
            print(f"{nome}: {len(itens)} manchetes")
        except Exception as e:
            problemas.append(nome)
            print(f"{nome}: FALHOU ({type(e).__name__}: {e})")

    if not noticias:
        print("Nenhuma fonte respondeu. O ficheiro anterior e mantido.")
        return 1

    noticias.sort(key=lambda n: n["data"] or "", reverse=True)
    noticias = noticias[:TOTAL_MAX]

    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump({
            "atualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fontes_com_falha": problemas,
            "noticias": noticias,
        }, f, ensure_ascii=False, indent=1)

    print(f"\n{len(noticias)} manchetes gravadas em {os.path.basename(SAIDA)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
