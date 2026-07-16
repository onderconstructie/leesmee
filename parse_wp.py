# -*- coding: utf-8 -*-
"""
parse_wp.py  -  WordPress-export (WXR) -> leesmee_data.json

Leest de export van asgaupaust.wordpress.com en giet alle gepubliceerde artikels in
een schone data.json voor de leesmee-site. Doet geen internet: puur lokaal parsen.

Ontwerpprincipes (zoals bij Denk mee met Mechelen):
  - Niets verzinnen. Thema's/dossiers komen uit een vaste taxonomie; de "beste van"
    komt letterlijk uit de links die het magazine zelf in zijn jaaroverzichten zette.
  - Data, geen handwerk. De taxonomie staat hier als data, niet handgeplakt in de HTML.
  - Inhoud en magazine centraal, niet de maker.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import html as htmllib
import hashlib
import json
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

BASE = Path(__file__).parent
NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
}
MAANDEN = ["", "januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]

# ---------------------------------------------------------------------------
# Thema's = de eigen rubrieken van het magazine, één-op-één uit de bron.
# Alleen de omschrijvingen zijn van de site; de indeling zelf wordt niet verzonnen.
# ---------------------------------------------------------------------------
THEMAS = [
    {"slug": "bestuur", "naam": "Bestuur",
     "omschrijving": "Het stadhuis zelf: het college, de gemeenteraad, openbaarheid, mandaten en de spelregels van de macht."},
    {"slug": "leven-wonen", "naam": "Leven & Wonen",
     "omschrijving": "Wonen en leven in de stad: ruimtelijke plannen, vastgoed, milieu en de leefomgeving."},
    {"slug": "faits-divers", "naam": "Faits divers",
     "omschrijving": "Cartoons, couleur locale en de lichtere kant van de stad."},
    {"slug": "budget", "naam": "Budget",
     "omschrijving": "De centen van de stad: de begroting, de schuld, subsidies en belastingen."},
    {"slug": "misdaad", "naam": "Misdaad",
     "omschrijving": "Politie, veiligheid en criminaliteit."},
    {"slug": "mobiliteit", "naam": "Mobiliteit",
     "omschrijving": "Verkeer en vervoer: parkeren, de fiets en de autoluwe binnenstad."},
    {"slug": "metier", "naam": "Metier",
     "omschrijving": "Over het vak: hoe de stukken gemaakt werden en wat het magazine onderweg bijleerde."},
    {"slug": "opinie", "naam": "Opinie",
     "omschrijving": "Duiding en commentaar, duidelijk gescheiden van het nieuws."},
    {"slug": "cultuur", "naam": "Cultuur",
     "omschrijving": "Cultuur en erfgoed in de stad."},
    {"slug": "werk", "naam": "Werk",
     "omschrijving": "Werk en economie in de stad."},
]
THEMA_SLUGS = {t["slug"] for t in THEMAS}

# ---------------------------------------------------------------------------
# Taxonomie: dossiers (meerjarige verhaallijnen; niet elke post zit in een dossier)
# ---------------------------------------------------------------------------
DOSSIERS = [
    {"slug": "pfos", "naam": "PFOS & de brandweerkazerne",
     "omschrijving": "Van blusschuim tot bodemvervuiling: hoe de stad al eind 2018 wist van de PFOS-verontreiniging bij de oude brandweerkazerne.",
     "tags": set(), "kw": ["pfos", "blusschuim", "brandweerkazerne", "dageraadstraat"]},
    {"slug": "comet-zorro", "naam": "Comet, Komet & Zorro",
     "omschrijving": "Het meerjarige dossier van vervuilde industriezone naar woonproject, met MER, RUP, ophoging en hoogbouw.",
     "tags": {"comet", "komet", "zorro"}, "kw": ["comet", "komet", "zorro"]},
    {"slug": "vesten", "naam": "De Vesten",
     "omschrijving": "De herinrichting van de Vesten en het burgerprotest eromheen.",
     "tags": set(), "kw": ["vesten"]},
    {"slug": "spreeuwenhoek", "naam": "Spreeuwenhoek",
     "omschrijving": "Geweigerde plannen, een arrest van de Raad van State en de opeenvolgende audits.",
     "tags": set(), "kw": ["spreeuwenhoek"]},
    {"slug": "schuldenberg", "naam": "De schuldenberg & de begroting",
     "omschrijving": "De Mechelse schuld, leningen en borgstellingen, plus de reeks begrotingskunde voor beginners.",
     "tags": {"schuld", "begrotingskunde"}, "kw": ["schuldenberg", "begrotingskunde", "miljoen euro schuld"]},
    {"slug": "mandaten", "naam": "Mandaten in het Staatsblad",
     "omschrijving": "Van mandatenkoningin Geypen tot de vergeten mandaten van Somers en het verdubbelde presentiegeld bij intercommunales.",
     "tags": {"mandaten"}, "kw": ["mandaat", "presentiegeld", "mandatenkoningin"]},
    {"slug": "gemeenteraad-live", "naam": "Gemeenteraad Live",
     "omschrijving": "De vlaggenschipreeks: per zitting een voorbeschouwing op de volledige agenda plus live verslag.",
     "tags": {"voorbeschouwing"}, "kw": ["voorbeschouwing", "gemeenteraad live"]},
    {"slug": "surveillance", "naam": "Camera's, profiling & privacy",
     "omschrijving": "Cameratoezicht, ANPR, online profiling en het opvragen van de foto's van alle Mechelaars uit het Rijksregister.",
     "tags": {"anpr", "camera", "privacy"}, "kw": ["profiling", "rijksregister", "anpr", "cameratoezicht"]},
    {"slug": "gas-autoluw", "naam": "GAS & de autoluwe zone",
     "omschrijving": "De jaarlijkse cijfers over foutparkeren, de autoluwe zone en de GAS-boetes.",
     "tags": {"gas"}, "kw": ["autoluw", "foutparkeren", "gas-boete", "gas geven"]},
    {"slug": "superdiversiteit", "naam": "Superdiversiteit",
     "omschrijving": "Een reeks factchecks op het superdiverse zelfbeeld van de stad: nationaliteiten, onderwijs en de huurmarkt.",
     "tags": {"diversiteit"}, "kw": ["superdivers", "nationaliteiten", "huurmarkt"]},
    {"slug": "dashboards", "naam": "Datatools & dashboards",
     "omschrijving": "Zelfgebouwde datatools over raadsleden, subsidies en het patrimonium van de stad.",
     "tags": {"dashboard"}, "kw": ["dashboard", "datatool"]},
    {"slug": "openbaarheid", "naam": "De WOB-strijd",
     "omschrijving": "Het doorlopende gevecht om openbaarheid: van grootste weigeraar tot beroepen bij de Vlaamse beroepsinstantie.",
     "tags": {"wob", "openbaarheid"}, "kw": ["openbaarheidsverzoek", "beroepsinstantie", "weigert", "weigerde"]},
]

# ---------------------------------------------------------------------------
# De aanpak: de drie basistechnieken (uit het method-manifest van het magazine),
# elk gekoppeld aan echte voorbeeldstukken via een slug-fragment.
# ---------------------------------------------------------------------------
AANPAK = [
    {"nr": "01", "titel": "Openbaarheid afdwingen",
     "omschrijving": "Documenten opvragen via de openbaarheidswetgeving, durven in beroep gaan (gratis in Vlaanderen) en desnoods een klacht indienen. Zo komen de basisdocumenten van de stad boven water.",
     "thema": "bestuur", "voorbeeld_kw": ["informatieveilig", "e-mails van ambtenaren openbaar", "verborgen agenda"]},
    {"nr": "02", "titel": "De gemeenteraad volgen",
     "omschrijving": "De agenda van de raad bepaalt de newsbeat, niet het persbericht. Van een korte voorbeschouwing tot een volledige agenda-duiding en een live verslag, met een dashboard over wie er opdaagt en wie er vragen stelt.",
     "thema": "bestuur", "voorbeeld_kw": ["staat van de mechelse gemeenteraad", "voorbeschouwing", "dashboard"]},
    {"nr": "03", "titel": "Leren in het openbaar",
     "omschrijving": "Openlijk tonen hoe een stuk gemaakt werd, en tegelijk zelf groeien in een onderwerp: reeksen als begrotingskunde voor beginners en een cursus statistiek voor wie het bestuur wil controleren.",
     "thema": "metier", "voorbeeld_kw": ["begrotingskunde", "statistiek", "percelen", "zomerklas", "chatgpt", "leerproces"]},
]

YEAR_OVERVIEW_RX = re.compile(
    r"(stukjes die je moest gelezen|fiere stukjes|verhalen waar we trots|blijven meedenken|paust ma gau eet)",
    re.IGNORECASE)


def txt(node, path):
    e = node.find(path, NS)
    return e.text if e is not None and e.text is not None else ""


# WordPress-shortcodes die de export als kale tekst achterlaat. We noemen ze bij NAAM en
# vangen dus niet elk blokje tussen rechte haken: "[UPDATE]" hoort bij een titel en moet
# blijven staan. Bij [caption ...]tekst[/caption] verdwijnt enkel het omhulsel; het bijschrift
# zelf is gewone tekst en blijft.
_SHORTCODE_RX = re.compile(
    r"\[/?(?:caption|gallery|embed|video|audio|playlist|googleapps|googlemaps|youtube|vimeo|"
    r"soundcloud|wpvideo|slideshow|contact-form|contact-field)\b[^\]]*/?\]",
    re.IGNORECASE)


def strip_shortcodes(s):
    return _SHORTCODE_RX.sub(" ", s)


# De WordPress-insluitingen van tweets, YouTube en Facebook bestaan op dit statische archief
# niet: hun URL bleef als kale, onaanklikbare tekst achter. 185 keer, in 68 stukken, en juist
# in de live-verslagen van de gemeenteraad, die de lezer zelf vragen om "door te klikken op een
# tweet". We maken er gewone links van.
#
# Dit zet GEEN cookies en breekt de belofte van de site niet: een <a> laadt niets in, er komt
# pas iets van Twitter of YouTube in beeld wanneer de bezoeker zelf klikt en dus zelf naar daar
# gaat. Dat is precies het verschil met een iframe, dat die diensten ONGEVRAAGD in de pagina
# trekt. De zichtbare tekst blijft de URL zelf: enkel de klik komt erbij.
_BESCHERMD_RX = re.compile(r"(<a\b[^>]*>.*?</a>|<[^>]+>)", re.DOTALL | re.IGNORECASE)
_KALE_URL_RX = re.compile(r"https?://[^\s<>\"']+")


def _linkify_tekst(s):
    def _mk(m):
        url = m.group(0)
        staart = ""
        # Leestekens horen bij de zin, niet bij de URL.
        while url and url[-1] in ".,;:!?)]":
            staart = url[-1] + staart
            url = url[:-1]
        veilig = url.replace("&", "&amp;").replace('"', "&quot;")
        return '<a href="%s" target="_blank" rel="noopener">%s</a>%s' % (veilig, veilig, staart)

    return _KALE_URL_RX.sub(_mk, s)


def linkify_kale_urls(h):
    """Maakt kale URL's klikbaar, maar raakt niets aan wat al een link of een tag is."""
    uit, pos = [], 0
    for m in _BESCHERMD_RX.finditer(h):
        uit.append(_linkify_tekst(h[pos:m.start()]))
        uit.append(m.group(0))          # bestaande <a>-blokken en tags: onaangeroerd
        pos = m.end()
    uit.append(_linkify_tekst(h[pos:]))
    return "".join(uit)


def strip_html(s):
    # Eerst de shortcodes: anders blijft [caption id="..." width="4096"] als tekst in de
    # excerpt staan, want strip_html kent enkel <tags>.
    s = strip_shortcodes(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


# De WordPress-plugins die Google Spreadsheets en Google Maps insloten, bestaan op dit
# statische archief niet. Zonder ingreep blijft hun shortcode als kale tekst in het artikel
# staan EN is het cijfermateriaal onbereikbaar: dat is het ergste van twee werelden, want juist
# bij deze stukken (subsidiedatabanken, agendapunten, het patrimonium) is de tabel het bewijs.
# We maken er een gewone link van, zodat de data bij het stuk blijft horen.
_GOOGLEMAPS_RX = re.compile(r"\[googlemaps\s+(https?://[^\s\]]+)[^\]]*\]", re.IGNORECASE)
_GOOGLEAPPS_RX = re.compile(
    r'\[googleapps\s+domain="([^"]+)"\s+dir="([^"]+)"(?:[^\]]*?query="([^"]*)")?[^\]]*\]',
    re.IGNORECASE)


def embeds_naar_links(s):
    def _maps(m):
        return ('<p class="oud-embed"><a href="%s" target="_blank" rel="noopener">'
                'Bekijk de kaart bij dit artikel &#8594;</a></p>' % htmllib.unescape(m.group(1)))

    def _apps(m):
        domein, pad, query = m.group(1), htmllib.unescape(m.group(2)), htmllib.unescape(m.group(3) or "")
        url = "https://%s.google.com/%s" % (domein, pad.lstrip("/"))
        if query:
            url += "?" + query
        return ('<p class="oud-embed"><a href="%s" target="_blank" rel="noopener">'
                'Bekijk de tabel bij dit artikel &#8594;</a></p>' % url)

    return _GOOGLEAPPS_RX.sub(_apps, _GOOGLEMAPS_RX.sub(_maps, s))


_JETPACK_WIDGET_RX = re.compile(
    r"<!--\s*wp:jetpack/repeat-visitor\b.*?<!--\s*/wp:jetpack/repeat-visitor\s*-->"
    r"|<!--\s*wp:jetpack/simple-payments\b.*?<!--\s*/wp:jetpack/simple-payments\s*-->"
    r"|<!--\s*wp:jetpack/contact-form\b.*?<!--\s*/wp:jetpack/contact-form\s*-->",
    re.DOTALL | re.IGNORECASE)

# Overgebleven support-banners van de oude site: 'steun ons'-slogans (witte tekst op een
# gekleurde banner waarvan de achtergrond verloren ging, dus onzichtbaar op het papier) plus de
# bijhorende steun-knoppen, en de oproep om een (intussen verwijderd) contactformulier in te vullen.
_PROMO_SLOGAN_HEX_RX = re.compile(  # slogans/ondertitels met expliciete witte kleur
    r'<!--\s*wp:paragraph\b[^>]*"color":\{"text":"#f{3,6}"\}[^>]*-->.*?<!--\s*/wp:paragraph\s*-->',
    re.DOTALL | re.IGNORECASE)
_PROMO_SLOGAN_GROOT_RX = re.compile(  # slogan-koppen op reuzenformaat (70/80px, enkel voor banners gebruikt)
    r'<!--\s*wp:paragraph\b(?:(?!<!--\s*/wp:paragraph).)*?font-size:\s*(?:70|80)px'
    r'(?:(?!<!--\s*/wp:paragraph).)*?<!--\s*/wp:paragraph\s*-->',
    re.DOTALL | re.IGNORECASE)
_STEUN_KNOP_RX = re.compile(  # knop-groepen die naar de (verdwenen) steunpagina linken
    r'<!--\s*wp:buttons\b(?:(?!<!--\s*/wp:buttons).)*?steun-jij-ons-ook'
    r'(?:(?!<!--\s*/wp:buttons).)*?<!--\s*/wp:buttons\s*-->',
    re.DOTALL | re.IGNORECASE)
_DOOD_FORMULIER_RX = re.compile(
    r'(?:<!--\s*wp:heading\b(?:(?!<!--\s*/wp:heading).)*?<!--\s*/wp:heading\s*-->\s*)?'
    r'<!--\s*wp:paragraph\b(?:(?!<!--\s*/wp:paragraph).)*?onderstaand contactformulier'
    r'(?:(?!<!--\s*/wp:paragraph).)*?<!--\s*/wp:paragraph\s*-->',
    re.DOTALL | re.IGNORECASE)


def strip_jetpack_widgets(s):
    """Dode widgets en support-banners uit de oude site verwijderen (betaalknoppen,
    contactformulieren, 'steun ons'-slogans en -knoppen): niet-functioneel of onzichtbaar op
    een statisch leesarchief."""
    s = _JETPACK_WIDGET_RX.sub("", s)
    s = _PROMO_SLOGAN_HEX_RX.sub("", s)
    s = _PROMO_SLOGAN_GROOT_RX.sub("", s)
    s = _STEUN_KNOP_RX.sub("", s)
    s = _DOOD_FORMULIER_RX.sub("", s)
    return s


_TAG_MET_STYLE_RX = re.compile(r'<\w+\b[^>]*\bstyle="[^"]*"[^>]*>', re.IGNORECASE)
_BG_HEX_RX = re.compile(r"background(?:-color)?:\s*(#[0-9a-fA-F]{3,8})\s*;?", re.IGNORECASE)
_EIGEN_KLEUR_RX = re.compile(r"(?<!-)\bcolor:\s*(#[0-9a-fA-F]{3,8})\s*;?", re.IGNORECASE)

# De kleuren van het thema. Draait de editie (dag/nacht), dan hoeven enkel deze waarden om:
# de weging hieronder kiest zelf welke inkt het haalt en is dus palet-onafhankelijk.
PAPIER = (245, 241, 232)      # --paper, de pagina waarop dit archief gelezen wordt
KAART = (255, 253, 247)       # --kaart-b, het vlak dat het thema onder een neutraal blok legt
INKT = (81, 74, 64)           # --ink-2, de lopende tekst
INKT_ALFA = 1.0               # op dag is de tekstkleur vast, niet doorzichtig
LINK_INKT = (200, 0, 84)      # --pink-text, de linkkleur van het thema
WIT = (255, 255, 255)         # het papier waarop de oude site geschreven werd

# De twee inkten die het thema op een vreemd vlak kan zetten, met hun bijhorende linkkleur.
INKT_DONKER = (20, 16, 9)     # op een licht vlak
LINK_DONKER = (179, 0, 74)    # --pink-deep
INKT_LICHT = (245, 241, 232)  # op een donker vlak
LINK_LICHT = (255, 77, 148)   # --eiland-pink

AA = 4.5                      # de leesdrempel waaronder tekst niet meer telt


def _hex_naar_rgb(waarde, achter):
    """'#rgb', '#rrggbb' of '#rrggbbaa' -> de kleur zoals ze te zien is, dus half-doorzichtige
    kleuren samengesteld op de achtergrond waarop ze liggen."""
    h = waarde.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        return None
    try:
        rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None
    if len(h) == 8:
        a = int(h[6:8], 16) / 255
        rgb = tuple(round(rgb[i] * a + achter[i] * (1 - a)) for i in range(3))
    return rgb


def _helderheid(rgb):
    """Relatieve luminantie (WCAG): 0 is zwart, 1 is wit."""
    def kanaal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * kanaal(rgb[0]) + 0.7152 * kanaal(rgb[1]) + 0.0722 * kanaal(rgb[2])


def _contrast(a, b):
    hoog, laag = sorted((_helderheid(a), _helderheid(b)), reverse=True)
    return (hoog + 0.05) / (laag + 0.05)


def _thema_inkt(vlak):
    """De tekstkleur van het thema zoals ze op dit vlak werkelijk valt: ze is deels
    doorzichtig, dus het vlak schemert erdoor en dat kost contrast."""
    return tuple(round(INKT[i] * INKT_ALFA + vlak[i] * (1 - INKT_ALFA)) for i in range(3))


def _voeg_klasse(tag, klasse):
    m = re.search(r'class="([^"]*)"', tag, re.IGNORECASE)
    if m:
        return tag[:m.end(1)] + " " + klasse + tag[m.end(1):]
    return re.sub(r"^<(\w+)", r'<\1 class="%s"' % klasse, tag, count=1)


_TAG_MET_BGCOLOR_RX = re.compile(r'<\w+\b[^>]*\sbgcolor=["\'][^"\']*["\'][^>]*>', re.IGNORECASE)
_BGCOLOR_RX = re.compile(r'\sbgcolor=(["\'])\s*(#?[0-9a-fA-F]{3,8})\s*\1', re.IGNORECASE)


def _bgcolor_naar_stijl(s):
    """De oude site zette tabelkleuren soms nog in het bgcolor-attribuut. Dat verhuist naar de
    stijl, zodat die kleuren mee gewogen worden."""
    def repl(m):
        tag = m.group(0)
        bm = _BGCOLOR_RX.search(tag)
        if not bm:
            return tag
        kleur = bm.group(2)
        if not kleur.startswith("#"):
            kleur = "#" + kleur
        tag = tag[:bm.start(0)] + tag[bm.end(0):]
        sm = re.search(r'style="([^"]*)"', tag, re.IGNORECASE)
        if sm:
            return tag[:sm.start(1)] + "background-color:%s;" % kleur + tag[sm.start(1):]
        return re.sub(r"^<(\w+)", r'<\1 style="background-color:%s"' % kleur, tag, count=1)
    return _TAG_MET_BGCOLOR_RX.sub(repl, s)


def _weeg_kleuren(s):
    """De oude site schreef donkere tekst op lichte vlakken; dit archief wordt op een donkere
    pagina gelezen. Elk vlak en elke tekstkleur wordt daarom gewogen tegen de achtergrond waar
    ze werkelijk op ligt. Neutrale vlakken (grijs, wit) dragen geen betekenis en laten hun
    kleur los; gekleurde markeringen houden ze, want dat was de nadruk van de auteur, en
    krijgen er donkere tekst bij. Een tekstkleur die onder de leesdrempel zakt, laat los, zodat
    het thema ze zet."""
    def repl(m):
        tag = m.group(0)
        sm = re.search(r'style="([^"]*)"', tag, re.IGNORECASE)
        stijl = sm.group(1)
        bgm = _BG_HEX_RX.search(stijl)
        vlak = _hex_naar_rgb(bgm.group(1), PAPIER) if bgm else PAPIER
        if vlak is None:
            return tag
        klassen = []
        if bgm:
            # de kleur zoals de auteur ze koos, dus op het witte papier van de oude site
            bedoeld = _hex_naar_rgb(bgm.group(1), WIT) or vlak
            if _contrast(_thema_inkt(vlak), vlak) < AA:  # de gewone tekstkleur zakt hier
                if max(bedoeld) - min(bedoeld) <= 16:  # enkel een grijswaarde: geen nadruk bedoeld
                    stijl = _BG_HEX_RX.sub("", stijl)
                    vlak = KAART
                    klassen.append("oud-vlak")
                else:
                    # een half-doorzichtige stift vertroebelt op een vreemde pagina tot een
                    # middentoon waar niets meer op leest; vastzetten op de gekozen kleur
                    stijl = _BG_HEX_RX.sub("background-color:#%02x%02x%02x;" % bedoeld, stijl, count=1)
                    vlak = bedoeld
                    # welke van de twee inkten haalt het hier?
                    if _contrast(INKT_DONKER, vlak) >= _contrast(INKT_LICHT, vlak):
                        klassen.append("oud-inkt-donker")
                    else:
                        klassen.append("oud-inkt-licht")
            # Een link moet op dit vlak even goed leesbaar zijn als de tekst. Kies de eerste
            # merkkleur die het haalt: roze-op-roze zakt vaak nét onder de drempel, en dan
            # houdt het diepere merkroze de link herkenbaar. Erft pas de tekstkleur als
            # geen enkele roze het haalt; de onderlijning blijft dan het houvast.
            for kleur, klasse in ((LINK_INKT, None), (LINK_DONKER, "oud-link-diep"),
                                  (LINK_LICHT, "oud-link-licht")):
                if _contrast(kleur, vlak) >= AA:
                    if klasse:
                        klassen.append(klasse)
                    break
            else:
                klassen.append("oud-paneel")
        km = _EIGEN_KLEUR_RX.search(stijl)
        if km:
            inkt = _hex_naar_rgb(km.group(1), vlak)
            if inkt is None or _contrast(inkt, vlak) < AA:
                stijl = _EIGEN_KLEUR_RX.sub("", stijl)
        stijl = re.sub(r";\s*;", ";", stijl).strip().strip(";").strip()
        tag = tag[:sm.start(0)] + (('style="%s"' % stijl) if stijl else "") + tag[sm.end(0):]
        tag = re.sub(r"\s+>$", ">", re.sub(r"<(\w+)\s{2,}", r"<\1 ", tag))
        for k in klassen:
            tag = _voeg_klasse(tag, k)
        return tag
    return _TAG_MET_STYLE_RX.sub(repl, s)


_FONT_PX_RX = re.compile(r"font-size:\s*(\d+(?:\.\d+)?)px\s*;?", re.IGNORECASE)
LEESMAAT_MIN = 13  # px; daaronder leest ook een bijschrift niet meer


def _merk_bijschriften(s):
    """De oude site zette haar beeldkredieten ('Foto: ...', 'Beeld: ...') op 10px vast. Die
    maat leest niet; ze wordt losgelaten zodat het thema er een bijschrift van maakt."""
    def repl(m):
        tag = m.group(0)
        sm = re.search(r'style="([^"]*)"', tag, re.IGNORECASE)
        fm = _FONT_PX_RX.search(sm.group(1))
        if not fm or float(fm.group(1)) >= LEESMAAT_MIN:
            return tag
        stijl = re.sub(r";\s*;", ";", _FONT_PX_RX.sub("", sm.group(1))).strip().strip(";").strip()
        tag = tag[:sm.start(0)] + (('style="%s"' % stijl) if stijl else "") + tag[sm.end(0):]
        tag = re.sub(r"\s+>$", ">", re.sub(r"<(\w+)\s{2,}", r"<\1 ", tag))
        return _voeg_klasse(tag, "oud-bijschrift")
    return _TAG_MET_STYLE_RX.sub(repl, s)


def _lokaal_beeld(url):
    """Een wordpress.com-afbeeldings-URL -> stabiel lokaal pad beelden/inline/<hash>.<ext>."""
    base = url.split("?")[0]
    m = re.search(r"\.(jpe?g|png|gif|webp)$", base, re.IGNORECASE)
    ext = ("." + m.group(1).lower().replace("jpeg", "jpg")) if m else ".jpg"
    h = hashlib.md5(base.encode("utf-8")).hexdigest()[:10]
    return "beelden/inline/%s%s" % (h, ext), base


def _verwerk_imgs(s, inline_map):
    """Inline <img>'s van wordpress.com naar lokale, zelf-gehoste paden herschrijven;
    dode externe beelden (google/facebook-restjes) verwijderen."""
    def repl(m):
        tag = m.group(0)
        sm = re.search(r'src=["\']([^"\']+)["\']', tag, re.IGNORECASE)
        if not sm:
            return tag
        url = sm.group(1)
        if "asgaupaust.wordpress.com" in url or "asgaupaust.files.wordpress.com" in url:
            lok, base = _lokaal_beeld(url)
            inline_map[lok] = base
            tag = tag[:sm.start(1)] + lok + tag[sm.end(1):]
            if "loading=" not in tag.lower():
                tag = tag.replace("<img", '<img loading="lazy"', 1)
            return tag
        if re.match(r"https?://", url):
            return ""  # dood extern beeld (google-cache/facebook-pixel): weg
        return tag
    return re.sub(r"<img\b[^>]*>", repl, s, flags=re.IGNORECASE)


def clean_content(raw, inline_map):
    """Legacy WordPress-content opschonen naar nette HTML."""
    s = raw
    # 1) dode scripts (jetpack/twitter) weg
    s = re.sub(r"<script\b[^>]*>.*?</script>", "", s, flags=re.DOTALL | re.IGNORECASE)
    # 2) [caption ...]<img ...> Bijschrift [/caption]  ->  <figure>...<figcaption>...</figcaption></figure>
    def caption_repl(m):
        inner = m.group(1).strip()
        img = re.search(r"<img[^>]*>", inner, flags=re.IGNORECASE)
        img_tag = img.group(0) if img else ""
        rest = strip_html(inner[img.end():]) if img else strip_html(inner)
        fig = "<figure>" + img_tag
        if rest:
            fig += "<figcaption>" + htmllib.escape(rest) + "</figcaption>"
        return fig + "</figure>"
    s = re.sub(r"\[caption[^\]]*\](.*?)\[/caption\]", caption_repl, s, flags=re.DOTALL | re.IGNORECASE)
    # 3) [tweet ...] / [embed]...[/embed] / [gallery ...] / overige shortcodes -> weg of naar link
    s = re.sub(r"\[embed[^\]]*\](.*?)\[/embed\]",
               lambda m: ' <a href="%s" rel="noopener">%s</a> ' % (m.group(1).strip(), m.group(1).strip()),
               s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"\[/?tweet[^\]]*\]", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\[/?gallery[^\]]*\]", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\[[a-zA-Z][^\]]{0,120}\]", "", s)  # overige losse shortcodes
    # 4) inline beelden zelf-hosten (en dode externe beelden weg)
    s = _verwerk_imgs(s, inline_map)
    # 5) kleuren en maten uit de oude site wegen tegen de pagina waarop nu gelezen wordt
    s = _bgcolor_naar_stijl(s)
    s = _weeg_kleuren(s)
    s = _merk_bijschriften(s)
    # 6) lege figure/alinea's opkuisen die na het strippen kunnen overblijven
    s = re.sub(r"<figure>\s*</figure>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<p>\s*</p>", "", s, flags=re.IGNORECASE)
    return s.strip()


def _knip(t, limit=230):
    """Netjes inkorten: liefst tot een zinseinde, anders tot een woordgrens met een beletselteken.
    Zo breekt geen enkele kaart-intro nog midden in een woord af."""
    t = t.strip()
    if len(t) <= limit:
        return t
    knip = t[:limit]
    zin = max(knip.rfind(". "), knip.rfind("! "), knip.rfind("? "))
    if zin >= int(limit * 0.55):
        return knip[:zin + 1].strip()
    spatie = knip.rfind(" ")
    if spatie > 0:
        knip = knip[:spatie]
    return knip.rstrip(" ,;:").strip() + "…"


def maak_excerpt(raw_content, expliciet):
    if expliciet.strip():
        return _knip(strip_html(expliciet))
    # eerste <h3> (de vetgezette lede) of anders de eerste <p>
    m = re.search(r"<h3[^>]*>(.*?)</h3>", raw_content, flags=re.DOTALL | re.IGNORECASE)
    if not m:
        m = re.search(r"<p[^>]*>(.*?)</p>", raw_content, flags=re.DOTALL | re.IGNORECASE)
    kern = strip_html(m.group(1)) if m else strip_html(raw_content)
    return _knip(kern)


def main():
    xmls = list((BASE / "export").glob("*.xml")) + list((BASE / "export").glob("*.wxr"))
    if not xmls:
        sys.exit("[STOP] Geen WXR-export gevonden in export/ (verwacht een .xml of .wxr).")
    bron = xmls[0]
    root = ET.parse(bron).getroot()
    items = root.findall(".//item")

    # attachment-map: post_id -> url  (voor de uitgelichte afbeelding)
    att = {}
    for it in items:
        if txt(it, "wp:post_type") == "attachment":
            pid = txt(it, "wp:post_id")
            url = txt(it, "wp:attachment_url")
            if pid:
                att[pid] = url

    ruwe = [it for it in items
            if txt(it, "wp:post_type") == "post" and txt(it, "wp:status") == "publish"]

    posts = []
    slug2id = {}
    year_overviews = []  # (jaar, post_id, ruwe_content)
    inline_map = {}      # beelden/inline/<hash>.<ext> -> bron-URL (voor fetch_beelden.py)

    for it in ruwe:
        pid = txt(it, "wp:post_id")
        titel = htmllib.unescape(txt(it, "title")).strip()
        slug = txt(it, "wp:post_name") or (re.sub(r"[^a-z0-9]+", "-", titel.lower()).strip("-"))
        datum_raw = txt(it, "wp:post_date") or txt(it, "pubDate")
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", datum_raw or "")
        if m:
            jaar, maand, dag = m.group(1), int(m.group(2)), int(m.group(3))
            datum_iso = "%s-%02d-%02d" % (jaar, maand, dag)
            datum_disp = "%d %s %s" % (dag, MAANDEN[maand], jaar)
        else:
            jaar, datum_iso, datum_disp = "", "", ""
        bron_url = txt(it, "link")

        cats, tags = [], []
        for c in it.findall("category"):
            naam = htmllib.unescape((c.text or "").strip())
            nn = c.get("nicename") or ""
            if c.get("domain") == "category":
                cats.append({"naam": naam, "slug": nn})
            elif c.get("domain") == "post_tag":
                tags.append({"naam": naam, "slug": nn})

        raw = embeds_naar_links(strip_jetpack_widgets(txt(it, "content:encoded")))
        html_clean = clean_content(raw, inline_map)
        woorden = len(strip_html(raw).split())
        leestijd = max(1, round(woorden / 200))
        excerpt = maak_excerpt(raw, txt(it, "excerpt:encoded"))

        # uitgelichte afbeelding via _thumbnail_id
        beeld_bron = None
        for meta in it.findall("wp:postmeta", NS):
            k = meta.find("wp:meta_key", NS)
            v = meta.find("wp:meta_value", NS)
            if k is not None and k.text == "_thumbnail_id" and v is not None and v.text in att:
                beeld_bron = att[v.text]
        ext = ".jpg"
        if beeld_bron:
            e = re.search(r"\.(jpe?g|png|gif)(?:\?|$)", beeld_bron, re.IGNORECASE)
            if e:
                ext = "." + e.group(1).lower().replace("jpeg", "jpg")
        beeld = ("beelden/" + pid + ext) if beeld_bron else None

        tagslugs = {t["slug"] for t in tags} | {t["naam"].lower() for t in tags}
        haystack = (titel + " " + slug + " " + " ".join(t["naam"] for t in tags)).lower()
        haystack_diep = (haystack + " " + strip_html(raw)[:800]).lower()

        # thema's = de rubrieken waarin het magazine dit stuk zelf plaatste
        thema_slugs = [c["slug"] for c in cats if c["slug"] in THEMA_SLUGS]
        if not thema_slugs:
            thema_slugs = ["faits-divers"]

        # dossiers toewijzen
        dossier_slugs = []
        for do in DOSSIERS:
            if (tagslugs & do["tags"]) or any(k in haystack_diep for k in do["kw"]):
                dossier_slugs.append(do["slug"])

        posts.append({
            "id": pid, "titel": titel, "slug": slug,
            "datum": datum_iso, "datum_disp": datum_disp, "jaar": jaar,
            "categorieen": cats, "tags": tags,
            "themas": thema_slugs, "dossiers": dossier_slugs,
            "excerpt": excerpt, "woorden": woorden, "leestijd": leestijd,
            "beeld": beeld, "beeld_bron": beeld_bron,
            "bron_url": bron_url, "html": html_clean,
            "zoek": strip_html(raw).lower()[:1400],
        })
        slug2id[slug] = pid
        if txt(it, "wp:post_name") and ("jaaroverzicht" in tagslugs or YEAR_OVERVIEW_RX.search(titel)):
            year_overviews.append((jaar, pid, raw, titel))

    # ---- interne kruisverwijzingen omzetten naar links binnen het archief ----
    #      (een <a> naar een eigen oud artikel -> #/artikel/<slug>, zodat de lezer in
    #      het archief blijft en de link niet afhangt van het oude wordpress-domein)
    INTERN_A_RX = re.compile(
        r'href=(["\'])https?://asgaupaust\.(?:be|wordpress\.com)/\d{4}/\d{2}/\d{2}/([a-z0-9\-]+)/?\1',
        re.IGNORECASE)

    def _intern(m):
        s = m.group(2).lower()
        return ('href="#/artikel/%s"' % s) if s in slug2id else m.group(0)

    # 1c) Wat daarna nog naar het OUDE asgaupaust.be wijst, is sinds het portaal daar staat
    #     een 404. Nagemeten op 16/07/2026 over alle 38 doelen die in de artikels voorkomen:
    #       29 leven nog op asgaupaust.wordpress.com     -> daarheen
    #        1 is opgevolgd door een eigen site          -> /denkmee/ -> denkmee.asgaupaust.be
    #        4 zijn overal weg, maar staan in het Internet Archive -> daarheen
    #     Artikel-URL's zijn hierboven al archief-routes geworden, dus die komen hier niet meer.
    OPGEVOLGD = {"/denkmee/": "https://denkmee.asgaupaust.be/"}
    ENKEL_IN_ARCHIEF = ("/actief-burgerschap/", "/steun-jij-ons-ook/", "/kantlijn/", "/tag/agenda/")
    OUD_HOST_RX = re.compile(r'href="https?://(?:www\.)?asgaupaust\.be(/[^"]*)?"', re.IGNORECASE)
    # Een tikfout uit de oude doos: "asgaupaust.be/steun-jij-ons-ook/" werd ooit zonder protocol
    # getypt, waardoor WordPress er een pad ONDER het artikel van maakte. 20 keer overgenomen.
    KAPOT_RELATIEF_RX = re.compile(r"^/\d{4}/\d{2}/\d{2}/[^/]+/asgaupaust\.be(/.*)$", re.IGNORECASE)

    def _oud_pad(m):
        pad = m.group(1) or "/"
        herstel = KAPOT_RELATIEF_RX.match(pad)
        if herstel:
            pad = herstel.group(1)
        kaal = pad.split("#")[0].split("?")[0]
        if kaal in OPGEVOLGD:
            return 'href="%s"' % OPGEVOLGD[kaal]
        if kaal in ENKEL_IN_ARCHIEF:
            return 'href="https://web.archive.org/web/2022/https://asgaupaust.be%s"' % pad
        return 'href="https://asgaupaust.wordpress.com%s"' % pad

    for p in posts:
        # Eerst linkify: een kale URL naar een eigen artikel wordt zo een link, en daarna zet
        # INTERN_A_RX die meteen om naar een archief-route in plaats van naar de dode oude site.
        # Pas daarna de oude paden: zo kapen we geen artikel-URL's die al een route werden.
        p["html"] = OUD_HOST_RX.sub(_oud_pad, INTERN_A_RX.sub(_intern, linkify_kale_urls(p["html"])))

    # ---- beste van: uit de links in de jaaroverzichten zelf ----
    # Niet elke interne link in een jaaroverzicht is een keuze: de lopende tekst verwijst
    # ook zijdelings naar andere stukken. Drie signalen uit de bron zelf bakenen de lijst af:
    #   1. een jaaroverzicht licht stukken UIT DAT JAAR uit, dus een link naar een ouder stuk
    #      is een terzijde en geen keuze. Zonder deze regel stonden er in "beste van 2022" een
    #      stuk uit 2018 en een uit 2019: het overzicht verwees ernaar in een zin die ze zelfs
    #      uitdrukkelijk "buiten beschouwing" liet;
    #   2. wijst het overzicht zijn keuzes aan met een "lees het (volledige) artikel"-link,
    #      dan zijn enkel die links de lijst;
    #   3. noemt de titel zelf een aantal ("Vijf verhalen..."), dan telt de lijst er zoveel.
    LINK_RX = re.compile(r"asgaupaust\.(?:be|wordpress\.com)/\d{4}/\d{2}/\d{2}/([a-z0-9\-]+)/?", re.IGNORECASE)
    ANCHOR_RX = re.compile(
        r'<a\b[^>]*href=(["\'])https?://asgaupaust\.(?:be|wordpress\.com)/\d{4}/\d{2}/\d{2}/([a-z0-9\-]+)/?[^"\']*\1[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL)
    LEES_RX = re.compile(r"lees het( volledige)? artikel", re.IGNORECASE)
    TELWOORD = {"twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6, "zeven": 7, "acht": 8, "negen": 9, "tien": 10}

    def _titel_aantal(t):
        m = re.search(r"\b(\d{1,2})\b", t)
        if m:
            return int(m.group(1))
        tl = t.lower()
        for w, n in TELWOORD.items():
            if re.search(r"\b" + w + r"\b", tl):
                return n
        return None

    beste_van = []
    overzicht_ids = {pid for _, pid, _, _ in year_overviews}
    id2jaar = {p["id"]: str(p.get("datum", ""))[:4] for p in posts}

    def _telt_mee(tid, pid, jaar):
        return (tid and tid != pid and tid not in overzicht_ids
                and id2jaar.get(tid) == str(jaar))

    for jaar, pid, raw, titel in year_overviews:
        kandidaten = []  # (post_id, is_leeslink)
        for mm in ANCHOR_RX.finditer(raw):
            tid = slug2id.get(mm.group(2).lower())
            if _telt_mee(tid, pid, jaar):
                kandidaten.append((tid, bool(LEES_RX.search(strip_html(mm.group(3))))))
        if not kandidaten:  # vangnet: kale URL's zonder <a>-tag
            for mm in LINK_RX.finditer(raw):
                tid = slug2id.get(mm.group(1).lower())
                if _telt_mee(tid, pid, jaar):
                    kandidaten.append((tid, False))
        if any(lees for _, lees in kandidaten):
            kandidaten = [k for k in kandidaten if k[1]]
        gelinkt, gezien = [], set()
        for tid, _ in kandidaten:
            if tid not in gezien:
                gezien.add(tid)
                gelinkt.append(tid)
        n = _titel_aantal(titel)
        if n:
            gelinkt = gelinkt[:n]
        intro = maak_excerpt(raw, "")
        beste_van.append({"jaar": jaar, "titel": titel, "overzicht_id": pid,
                          "intro": intro, "post_ids": gelinkt})
    beste_van.sort(key=lambda b: b["jaar"])

    # ---- de aanpak: koppel elke techniek aan echte voorbeeldstukken ----
    id2post = {p["id"]: p for p in posts}
    aanpak = []
    for a in AANPAK:
        vb = []
        for p in posts:
            h = (p["titel"] + " " + p["slug"]).lower()
            if any(k in h for k in a["voorbeeld_kw"]):
                vb.append(p["id"])
            if len(vb) >= 4:
                break
        aanpak.append({**{k: a[k] for k in ("nr", "titel", "omschrijving", "thema")},
                       "voorbeeld_ids": vb})

    # ---- tellingen per thema/dossier ----
    themas_out = []
    for th in THEMAS:
        n = sum(1 for p in posts if th["slug"] in p["themas"])
        themas_out.append({"slug": th["slug"], "naam": th["naam"],
                           "omschrijving": th["omschrijving"], "count": n})
    dossiers_out = []
    for do in DOSSIERS:
        leden = [p for p in posts if do["slug"] in p["dossiers"]]
        if len(leden) < 2:
            continue  # een dossier is pas een dossier vanaf 2 stukken
        jaren = sorted({p["jaar"] for p in leden if p["jaar"]})
        dossiers_out.append({"slug": do["slug"], "naam": do["naam"],
                             "omschrijving": do["omschrijving"], "count": len(leden),
                             "jaar_van": jaren[0] if jaren else "", "jaar_tot": jaren[-1] if jaren else "",
                             "post_ids": [p["id"] for p in sorted(leden, key=lambda x: x["datum"])]})
    # dossier-slugs die het niet haalden (te weinig stukken) uit de posts wissen
    geldige_dossiers = {d["slug"] for d in dossiers_out}
    for p in posts:
        p["dossiers"] = [d for d in p["dossiers"] if d in geldige_dossiers]

    # ---- gerelateerde stukken (zelfde dossier eerst, dan gedeelde tags) ----
    for p in posts:
        scores = []
        ptags = {t["slug"] for t in p["tags"]}
        for q in posts:
            if q["id"] == p["id"]:
                continue
            sc = 3 * len(set(p["dossiers"]) & set(q["dossiers"]))
            sc += 2 * len(ptags & {t["slug"] for t in q["tags"]})
            sc += len(set(p["themas"]) & set(q["themas"]))
            if sc:
                scores.append((sc, q["datum"], q["id"]))
        scores.sort(reverse=True)
        p["gerelateerd"] = [i for _, _, i in scores[:4]]

    # ---- in welke "beste van"-jaargang zit een post ----
    for p in posts:
        p["beste_van"] = [b["jaar"] for b in beste_van if p["id"] in b["post_ids"]]

    posts.sort(key=lambda p: p["datum"], reverse=True)
    jaren = sorted({p["jaar"] for p in posts if p["jaar"]}, reverse=True)

    data = {
        "titel": "Lees mee met Mechelen",
        "ondertitel": "het archief van As Gau Paust",
        "is_demo": False,
        "counts": {"posts": len(posts), "themas": len([t for t in themas_out if t["count"]]),
                   "dossiers": len(dossiers_out), "jaren": len(jaren),
                   "met_beeld": sum(1 for p in posts if p["beeld"])},
        "jaren": jaren,
        "themas": [t for t in themas_out if t["count"]],
        "dossiers": dossiers_out,
        "beste_van": beste_van,
        "aanpak": aanpak,
        "inline_beelden": inline_map,
        "posts": posts,
    }

    uit = BASE / "leesmee_data.json"
    uit.write_text(json.dumps(data, ensure_ascii=False, indent=None), encoding="utf-8")

    print("Klaar. leesmee_data.json geschreven.")
    print("  posts:            %d" % len(posts))
    print("  met uitgelicht beeld: %d" % data["counts"]["met_beeld"])
    print("  jaren:            %s" % ", ".join(jaren))
    print("  thema's (met inhoud): %d" % data["counts"]["themas"])
    for t in themas_out:
        print("     - %-16s %3d  %s" % (t["slug"], t["count"], t["naam"]))
    print("  dossiers:         %d" % len(dossiers_out))
    for d in dossiers_out:
        print("     - %-16s %3d  (%s-%s)  %s" % (d["slug"], d["count"], d["jaar_van"], d["jaar_tot"], d["naam"]))
    print("  beste van:        %d jaargangen" % len(beste_van))
    for b in beste_van:
        print("     - %s  %2d stukken  %s" % (b["jaar"], len(b["post_ids"]), b["titel"][:48]))
    print("  aanpak-technieken:%d" % len(aanpak))
    for a in aanpak:
        print("     - %s %-24s voorbeelden: %d" % (a["nr"], a["titel"], len(a["voorbeeld_ids"])))


if __name__ == "__main__":
    main()
