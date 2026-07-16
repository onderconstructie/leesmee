# -*- coding: utf-8 -*-
"""
fetch_beelden.py  -  uitgelichte afbeeldingen same-origin binnenhalen

Downloadt per post de uitgelichte afbeelding (uit leesmee_data.json -> beeld_bron)
naar beelden/<id>.<ext>, zodat de site de beelden zelf host en er geen bezoekers-IP
naar wordpress.com gaat (zelfde principe als de zelf-gehoste fonts).

  - Verkleint via de wordpress.com-parameter ?w=1200 (scheelt fors in bestandsgrootte).
  - Idempotent: bestaat het bestand al, dan slaat hij het over.
  - Beleefd tegen de bron: identificeerbare User-Agent, 1 verzoek per ~0,25 s.

Vereist enkel `requests`  (python -m pip install requests).
"""
from pathlib import Path
import json
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

try:
    import requests
except ImportError:
    sys.exit("[STOP] 'requests' ontbreekt. Installeer met: python -m pip install requests")

BASE = Path(__file__).parent
BREEDTE = 1200
UA = "leesmee-archief/1.0 (+https://leesmee.asgaupaust.be) archiefopbouw"


def haal(sess, url, doel):
    """Eén afbeelding verkleind ophalen naar doel. Geeft 'nieuw'/'over'/'fout' terug."""
    doel = Path(doel)
    if doel.exists() and doel.stat().st_size > 0:
        return "over"
    doel.parent.mkdir(parents=True, exist_ok=True)
    vraag = url + (("&" if "?" in url else "?") + "w=%d" % BREEDTE)
    try:
        r = sess.get(vraag, timeout=30)
        r.raise_for_status()
        doel.write_bytes(r.content)
        return "nieuw"
    except Exception as e:
        print("  ! mislukt: %s (%s)" % (url, e))
        return "fout"


def main():
    data = json.loads((BASE / "leesmee_data.json").read_text(encoding="utf-8"))
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})

    # 1) uitgelichte beelden (per post)
    feat = [(BASE / p["beeld"], p["beeld_bron"]) for p in data["posts"]
            if p.get("beeld") and p.get("beeld_bron")]
    # 2) inline beelden uit de artikelteksten (beelden/inline/<hash>.<ext> -> bron-URL)
    inline = [(BASE / lok, url) for lok, url in (data.get("inline_beelden") or {}).items()]

    alle = feat + inline
    tel = {"nieuw": 0, "over": 0, "fout": 0}
    for i, (doel, url) in enumerate(alle, 1):
        r = haal(sess, url, doel)
        tel[r] += 1
        if r == "nieuw":
            time.sleep(0.25)
            if tel["nieuw"] % 25 == 0:
                print("  ... %d gedownload (%d/%d bekeken)" % (tel["nieuw"], i, len(alle)))

    print("Klaar. uitgelicht: %d, inline: %d, samen %d beelden."
          % (len(feat), len(inline), len(alle)))
    print("       nieuw: %d, overgeslagen: %d, mislukt: %d"
          % (tel["nieuw"], tel["over"], tel["fout"]))


if __name__ == "__main__":
    main()
