# -*- coding: utf-8 -*-
"""
build.py  -  template.html + leesmee_data.json  ->  dist/index.html

Bouwt het zelfstandige leesarchief: de data wordt in de UI-schil gespoten, de
zelf-gehoste fonts en de uitgelichte beelden gaan mee naar dist/. Geen internet.
"""
from pathlib import Path
import sys
import os
import re
import json
import shutil

from PIL import Image

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

# 2b) De echte afmetingen van de handboek-cartoons meegeven. Zonder width/height reserveert
#     de browser geen ruimte: de omdraaikaart klapte in tot enkel haar hint (nagemeten
#     210x44 in plaats van 210x284) en de tekst sprong zodra het beeld binnenkwam. We meten
#     ze hier in plaats van ze in te tikken, zodat een volgende cartoon vanzelf klopt.
beeld_maten = {}
for _rel in sorted(set(re.findall(r"beeld:'([^']+)'", template))):
    _pad = BASE / _rel
    if not _pad.exists():
        print("       LET OP: handboek-beeld ontbreekt: %s" % _rel)
        continue
    with Image.open(_pad) as _im:
        beeld_maten[_rel] = list(_im.size)
html = html.replace("__BEELDMATEN__", json.dumps(beeld_maten, ensure_ascii=False))
print("       handboek-beelden gemeten: %s" % (", ".join("%s %dx%d" % (k.split("/")[-1], v[0], v[1])
                                                         for k, v in beeld_maten.items()) or "geen"))

# 2c) Veiligheidsklep: geen e-mailadressen op de site. Deze bouw vertrekt bij elke publicatie
#     opnieuw van de rauwe WordPress-export, en die bevat contactformulier-inzendingen en
#     betaalorders. parse_wp.py filtert daar structureel op gepubliceerde artikels, maar in de
#     artikeltekst zelf staan soms adressen (een dienstadres van de stad, een lezer die reageert).
#     Denk mee weigert al te bouwen bij zo'n adres; hier gebeurde dat niet, en dus stond er één
#     in de gepubliceerde site. Zelfde klep, zelfde plek: vóór het schrijven van dist/.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = set()          # bewuste uitzonderingen; leeg tot er een reden is
_lek = sorted({m.group(0) for m in EMAIL_RE.finditer(html)} - EMAIL_OK)
if _lek:
    sys.exit("[STOP] Build geweigerd: e-mailadres(sen) in de site: %s\n"
             "       Haal ze uit de brontekst (parse_wp.py schoont die) of zet ze bewust in "
             "EMAIL_OK hierboven." % ", ".join(_lek[:5]))
print("       e-mailcontrole: geen adressen in de site ✓")

# 3) Eindproduct schrijven.
out_dir = BASE / "dist"
out_dir.mkdir(exist_ok=True)
(out_dir / "index.html").write_text(html, encoding="utf-8")

# 4) CNAME voor het eigen subdomein op GitHub Pages (altijd meegeschreven).
#    Eenmalig: Settings -> Pages -> Custom domain = dit domein, en een DNS
#    CNAME-record 'leesmee' -> '<jouw-gebruiker>.github.io'.
(out_dir / "CNAME").write_text(CUSTOM_DOMAIN + "\n", encoding="utf-8")

# robots.txt. Er stond er geen, dus elke bot kreeg tot nu toe helemaal geen signaal (en bij een
# eigen domein zet GitHub Pages er zelf niets neer). Bewust OPEN: dit archief bestaat om gelezen
# te worden, en het project draait om hergebruik. Enkel de eigen foutpagina blijft eruit.
ROBOTS = """# %s
# Van harte welkom. Deze site is openbaar en mag gelezen, geciteerd en hergebruikt worden.
# De code staat publiek. Wil je zoiets voor je eigen stad bouwen, neem gerust contact op.
User-agent: *
Allow: /
Disallow: /404.html
"""
(out_dir / "robots.txt").write_text(ROBOTS % CUSTOM_DOMAIN, encoding="utf-8")

# 4b) Eigen 404-pagina. Zonder dit bestand toont GitHub Pages zijn Engelstalige "Page not
#     found": geen merk, geen Nederlands, geen weg terug. Eén tikfout in een gedeelde link
#     volstaat. De hash-routes vangt de site zelf op; dit is voor echte verkeerde paden.
#     Zelfstandig bestand met eigen stijl inline.
PAGINA_404 = """<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#FF0066">
<title>Pagina niet gevonden, Lees mee met Mechelen</title>
<meta name="robots" content="noindex">
<link rel="icon" type="image/png" href="/beelden/mug.png">
<style>
@font-face{font-family:'Geist';font-style:normal;font-weight:100 900;font-display:swap;src:url('/fonts/geist-var.woff2') format('woff2')}
@font-face{font-family:'JetBrains Mono';font-style:normal;font-weight:100 800;font-display:swap;src:url('/fonts/jbmono-var.woff2') format('woff2')}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:#f5f1e8;color:#2b2621;font-family:'Geist',system-ui,sans-serif;line-height:1.6;padding:1.5rem}
.doos{max-width:34rem;text-align:center}
.mug{width:96px;height:96px;border-radius:50%;margin:0 auto 1.6rem;display:block}
.code{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:.72rem;letter-spacing:.14em;
  text-transform:uppercase;color:#c80054;margin:0 0 .6rem}
h1{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:clamp(1.5rem,5vw,2.2rem);
  font-weight:600;letter-spacing:-.02em;margin:0 0 .9rem}
p{color:#514a40;margin:0 0 1.8rem}
.wegen{display:flex;flex-wrap:wrap;gap:.7rem;justify-content:center}
.wegen a{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:.74rem;letter-spacing:.06em;
  text-transform:uppercase;text-decoration:none;padding:.7rem 1.1rem;border-radius:999px;
  border:1px solid rgba(0,0,0,.18);color:#2b2621;transition:.15s}
.wegen a:hover{border-color:#FF0066;color:#c80054}
.wegen a.prim{background:#FF0066;border-color:#FF0066;color:#fff}
.wegen a.prim:hover{background:#b3004a;border-color:#b3004a;color:#fff}
</style>
</head>
<body>
  <main class="doos">
    <img class="mug" src="/beelden/mug.png" alt="" aria-hidden="true" width="512" height="512">
    <p class="code">Fout 404</p>
    <h1>Deze pagina bestaat niet</h1>
    <p>Misschien is de link verouderd, of staat er een tikfout in het adres.
       Hieronder raak je weer op weg.</p>
    <div class="wegen">
      <a class="prim" href="/">Naar Lees mee</a>
      <a href="https://denkmee.asgaupaust.be/">Denk mee</a>
      <a href="https://asgaupaust.be/">As Gau Paust</a>
    </div>
  </main>
</body>
</html>
"""
(out_dir / "404.html").write_text(PAGINA_404, encoding="utf-8")

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
