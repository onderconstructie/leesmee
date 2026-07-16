# -*- coding: utf-8 -*-
"""
build.py  -  template.html + leesmee_data.json  ->  dist/index.html

Bouwt het zelfstandige leesarchief: de data wordt in de UI-schil gespoten, de
zelf-gehoste fonts en de uitgelichte beelden gaan mee naar dist/. Geen internet.
"""
from pathlib import Path
import sys
import os
import json
import shutil

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

BASE = Path(__file__).parent
CUSTOM_DOMAIN = "leesmee.asgaupaust.be"

# 1) UI-schil + data lezen.
template = (BASE / "template.html").read_text(encoding="utf-8")
data = json.loads((BASE / "leesmee_data.json").read_text(encoding="utf-8"))

# 1b) Velden die enkel de pijplijn nodig heeft (de bron-URL's voor fetch_beelden.py)
#     uit het gepubliceerde bestand halen: de frontend gebruikt ze niet, en zo lekken
#     er geen wordpress.com-URL's mee in de HTML.
for _p in data.get("posts", []):
    _p.pop("beeld_bron", None)
data.pop("inline_beelden", None)

# 2) Data als JS-object-literal in de placeholder. "</" -> "<\/" zodat een letterlijke
#    "</script>" in een brontekst de <script>-tag niet vroegtijdig kan sluiten.
data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
html = template.replace("__LEESMEE_DATA__", data_json)

# 3) Eindproduct schrijven.
out_dir = BASE / "dist"
out_dir.mkdir(exist_ok=True)
(out_dir / "index.html").write_text(html, encoding="utf-8")

# 4) CNAME voor het eigen subdomein op GitHub Pages (altijd meegeschreven).
#    Eenmalig: Settings -> Pages -> Custom domain = dit domein, en een DNS
#    CNAME-record 'leesmee' -> '<jouw-gebruiker>.github.io'.
(out_dir / "CNAME").write_text(CUSTOM_DOMAIN + "\n", encoding="utf-8")

# 5) Zelf-gehoste lettertypes meekopieren naar dist/fonts/ (woff2 + OFL-licenties).
fonts_src = BASE / "fonts"
if fonts_src.exists():
    fonts_dst = out_dir / "fonts"
    fonts_dst.mkdir(exist_ok=True)
    n = 0
    for f in fonts_src.iterdir():
        if f.suffix.lower() in (".woff2", ".txt"):
            shutil.copy2(f, fonts_dst / f.name)
            n += 1
    print("       fonts gekopieerd naar dist/fonts/: %d bestanden" % n)

# 6) Uitgelichte beelden meekopieren naar dist/beelden/ (same-origin, geen hotlink
#    naar wordpress.com). Enkel kopieren wat nog niet (identiek) in dist/ staat.
beelden_src = BASE / "beelden"
if beelden_src.exists():
    beelden_dst = out_dir / "beelden"
    n = aanwezig = 0
    for wortel, _dirs, files in os.walk(beelden_src):
        rel = Path(wortel).relative_to(beelden_src)
        (beelden_dst / rel).mkdir(parents=True, exist_ok=True)
        for name in files:
            aanwezig += 1
            bron = Path(wortel) / name
            doel = beelden_dst / rel / name
            if not doel.exists() or doel.stat().st_size != bron.stat().st_size:
                shutil.copy2(bron, doel)
                n += 1
    print("       beelden in dist/beelden/: %d (nieuw gekopieerd: %d)" % (aanwezig, n))

demo = "  (LET OP: is_demo staat op true)" if data.get("is_demo") else ""
print("Klaar! dist/index.html gebouwd: %d posts, %s tekens%s" % (len(data["posts"]), format(len(html), ","), demo))
print("       CNAME: %s" % CUSTOM_DOMAIN)
