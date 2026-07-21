# Lees mee

Het **leesarchief van As Gau Paust**: zeven jaar hyperlokale journalistiek over Mechelen
(2016 tot 2023), niet chronologisch gedumpt maar gebundeld per **thema** en **dossier**,
met de sterkste stukken zoals het magazine ze destijds zelf uitlichtte, en met **de aanpak**
erbij (de formule met zeven technieken achter de journalistiek).

Zusje van [Denk mee met Mechelen](https://denkmee.asgaupaust.be). Zelfde familie, ander
werk: het ene volgt de stad van vandaag, het andere bewaart wat er al geschreven werd.
De hele site is één zelfstandig, te uploaden geheel: `dist/`.

Onderdeel van asgaupaust.be. De inhoud en het magazine staan centraal, niet de maker.

---

## Snelstart

```bash
python -m pip install requests     # enkel nodig om de beelden op te halen
python run_all.py                  # de hele pijplijn -> dist/
```

Open daarna `dist/index.html` in een browser, of upload de map `dist/` naar je webhost.

---

## De pijplijn (`run_all.py`)

| # | Stap | Wat | Internet? |
|---|------|-----|-----------|
| 1 | `parse_wp.py` | WordPress-export (`export/*.wxr`) → `leesmee_data.json`: schone artikels, thema's, dossiers, beste van | nee |
| 2 | `fetch_beelden.py` | Uitgelichte én inline beelden verkleind same-origin ophalen naar `beelden/` | ja (optioneel) |
| 3 | `build.py` | `template.html` + data → `dist/index.html` (+ fonts + beelden, CNAME) | nee |

Stap 2 is idempotent (bestaande beelden worden overgeslagen) en faalt zacht: zonder
`requests` of zonder internet bouwt de site gewoon verder met wat er al is.

### Hoe de bundeling ontstaat (`parse_wp.py`)

- **Thema's** zijn de **eigen rubrieken van het magazine** (de categorieën uit de bron),
  één-op-één overgenomen. **Dossiers** komen uit een vaste taxonomie (bovenin het script
  als data), toegewezen op tag en trefwoord.
- **Beste van** wordt niet verzonnen: het script leest de links die het magazine zelf in
  zijn jaaroverzichten zette, en bundelt net die stukken per jaargang.
- **De aanpak** (de formule, zeven technieken) komt uit het method-manifest van het magazine
  en linkt naar echte voorbeeldstukken uit het archief.
- **Verwante stukken** worden bepaald op gedeeld dossier, tag en thema.

---

## Ontwerpprincipes

- **Inhoud en magazine centraal**, niet de maker.
- **Niets verzinnen.** Thema's zijn de eigen rubrieken van het magazine; de "beste van"
  komt letterlijk uit de eigen jaaroverzichten.
- **Data, geen handwerk.** De taxonomie staat als data, niet handgeplakt in de HTML.
- **Alles same-origin.** Fonts (Geist + JetBrains Mono) en álle beelden worden zelf gehost:
  geen bezoekers-IP naar Google of wordpress.com, en niets breekt als de oude site verdwijnt.

---

## Privacy en de export

De rauwe WordPress-export (`export/*.wxr`) staat in `.gitignore` en hoort **niet** in de
publieke repo: ze bevat contactformulier-inzendingen en betaalorders. Enkel de gepubliceerde
artikels belanden, via `leesmee_data.json`, op de site. Dat databestand én de gebouwde `dist/`
worden wel meegecommit, zodat de site herbouwbaar blijft zonder de export.

---

## Publiceren

`dist/` is de publiceerbare map. Voor de gratis weg ligt een GitHub Pages-workflow klaar in
`.github/workflows/pages.yml`: zet **Settings → Pages → Source = "GitHub Actions"**.

Voor het eigen subdomein `leesmee.asgaupaust.be`:

1. Een **aparte repo** (één custom domein per Pages-site).
2. DNS: een `CNAME`-record `leesmee` → `<jouw-github-gebruiker>.github.io`.
3. `build.py` schrijft `dist/CNAME` al mee.

Publiceren gaat met `deploy.bat` (bouwen, committen, pushen).

---

## Bestanden

- `parse_wp.py` — WXR → `leesmee_data.json` (de bundeling)
- `fetch_beelden.py` — beelden same-origin ophalen
- `build.py` — `dist/index.html` bouwen
- `run_all.py` — de startknop (orkestreert alles)
- `template.html` — de UI-schil (placeholder `__LEESMEE_DATA__`, client-side gerenderd)
- `leesmee_data.json` — alle verwerkte artikels + taxonomie
- `fonts/` — Geist + JetBrains Mono (woff2 + OFL-licenties)
- `dist/` — het eindproduct (index.html + CNAME + fonts + beelden)
- `export/` — de rauwe WordPress-export *(niet in de repo)*

---

Het archief is geen eindpunt maar een leesplek: een manier om zeven jaar stadsjournalistiek
terug te vinden, te verbinden, en zelf mee aan de slag te gaan.
