# Lees mee met Mechelen

Het leesarchief van As Gau Paust: zeven jaar hyperlokale journalistiek over Mechelen
(2016 tot 2023), gebundeld per thema en dossier, met de formule erbij: zeven overdraagbare
technieken om een stad transparant te maken. Live op
[leesmee.asgaupaust.be](https://leesmee.asgaupaust.be), onderdeel van
[asgaupaust.be](https://asgaupaust.be).

Wat het archief is en hoe de formule werkt, staat op de site zelf; deze README herhaalt
dat bewust niet. Wat er met bezoekersgegevens gebeurt:
[asgaupaust.be/privacy](https://asgaupaust.be/privacy/).

## Zelf draaien

```bash
python -m pip install requests     # enkel nodig om de beelden op te halen
python run_all.py                  # de hele pijplijn → dist/
```

`run_all.py` orkestreert de stappen; elk script documenteert zichzelf in zijn docstring.
De rauwe WordPress-export (`export/*.wxr`) staat bewust niet in de repo; enkel de
gepubliceerde artikels gaan, via `leesmee_data.json`, mee naar de site.

## Publiceren

`dist/` is de publiceerbare map: upload ze, of gebruik de GitHub Pages-workflow
(`.github/workflows/pages.yml`, Settings → Pages → Source = "GitHub Actions").
