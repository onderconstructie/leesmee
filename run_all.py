# -*- coding: utf-8 -*-
"""
run_all.py  -  de startknop van het leesarchief

Draait de hele pijplijn in volgorde:
  1) parse_wp.py      WordPress-export (export/*.wxr) -> leesmee_data.json     (geen internet)
  2) fetch_beelden.py uitgelichte beelden same-origin binnenhalen              (internet, optioneel)
  3) build.py         template.html + data -> dist/index.html (+ fonts + beelden, CNAME)

Stap 2 is idempotent (bestaande beelden worden overgeslagen) en faalt zacht:
zonder 'requests' of zonder internet bouwt de site gewoon verder met wat er is.
"""
from pathlib import Path
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

BASE = Path(__file__).parent


def run(script, verplicht=True):
    print("\n===== %s =====" % script)
    r = subprocess.run([sys.executable, str(BASE / script)])
    if r.returncode != 0:
        if verplicht:
            sys.exit("[STOP] %s faalde (returncode %d)." % (script, r.returncode))
        print("   (%s faalde, maar is optioneel: we bouwen verder.)" % script)
    return r.returncode == 0


def main():
    run("parse_wp.py", verplicht=True)
    run("fetch_beelden.py", verplicht=False)   # optioneel: internet + requests
    run("build.py", verplicht=True)
    print("\nAlles klaar. Publiceer met deploy.bat, of upload de map dist/ naar je webhost.")


if __name__ == "__main__":
    main()
