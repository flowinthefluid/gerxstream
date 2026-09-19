# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showGenre:    48 Stunden
# showEntries:   3 Stunden
#
# Anime-Loads steht hinter DDoS-Guard. Ohne hinterlegte oder ueber
# FlareSolverr beschaffte Sitzung antwortet die Seite durchgaengig mit 403 -
# siehe resources/lib/handler/protection.py und die Einstellungen
# "Bot-Schutz" dieser Quelle.
#
# Aufbau der Seite (belegt an einem Archiv-Schnappschuss, weil die Seite von
# der Entwicklungsumgebung aus nicht erreichbar war):
#   Uebersicht  <a href=".../media/<slug>" class="cover-img"><img src="...">
#   Titel       <a href=".../media/<slug>" ... title="<voller Titel>">
#   Detailseite Folgenbloecke mit data-enc="<base64>", Inhalt wird per AJAX
#               nachgeladen (al.ajaxURL) und ist teils durch ein Captcha
#               geschuetzt.

import base64
import json

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'animeloads'
SITE_NAME = 'Anime-Loads'
SITE_ICON = 'animeloads.png'

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'www.anime-loads.org')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_SEARCH = URL_MAIN + '/search?q=%s'
URL_AJAX = URL_MAIN + '/ajax/'

# Rubriken der Seite, Pfad -> Menuename.
SECTIONS = (
    ('anime-series', 'Anime Series'),
    ('anime-movies', 'Anime Movies'),
    ('ova', 'OVA'),
    ('web', 'Web'),
    ('live-action', 'Live Action'),
    ('asia-movies', 'Asia Movies'),
    ('status/running', 'Laufend'),
    ('status/complete', 'Abgeschlossen'),
    ('all', 'Alle'),
)

# Kachel und zugehoeriger Titel. Der volle Titel steht im title-Attribut,
# der sichtbare Text ist gekuerzt ("Cardfight!&hellip;s Season 2").
ITEM_PATTERN = (r'href="[^"]*/media/([^"]+)"\s+class="cover-img">\s*'
                r'<img src="([^"]+)"')
TITLE_PATTERN = r'href="[^"]*/media/%s"[^>]*title="([^"]*)"'


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    for path, title in SECTIONS:
        params.setParam('sUrl', '%s/%s' % (URL_MAIN, path))
        cGui().addFolder(cGuiElement(title, SITE_IDENTIFIER, 'showEntries'), params)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')

    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, False):
        oRequest.cacheTime = 60 * 60 * 3  # 3 Stunden
    sHtmlContent = oRequest.request()
    if not sHtmlContent:
        # Bei aktiver Sperre liefert der requestHandler einen leeren Inhalt
        # und hat den Nutzer bereits auf die Bot-Schutz-Einstellungen
        # hingewiesen; hier waere eine zweite Meldung nur Laerm.
        if not sGui:
            oGui.showInfo()
        return

    isMatch, aResult = cParser.parse(sHtmlContent, ITEM_PATTERN)
    if not isMatch:
        if not sGui:
            oGui.showInfo()
        return

    seen = set()
    entries = []
    for sSlug, sImage in aResult:
        if sSlug in seen:
            continue
        seen.add(sSlug)
        isTitle, sTitle = cParser.parseSingleResult(
            sHtmlContent, TITLE_PATTERN % cParser.escape(sSlug))
        sName = sTitle.strip() if isTitle and sTitle.strip() else sSlug.replace('-', ' ').title()
        entries.append((sSlug, sName, sImage))

    total = len(entries)
    for sSlug, sName, sImage in entries:
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('tvshow')
        if sImage:
            oGuiElement.setThumbnail(sImage)
        params.setParam('entryUrl', '%s/media/%s' % (URL_MAIN, sSlug))
        params.setParam('sName', sName)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        oGui.setView('tvshows')
        oGui.setEndOfDirectory()


def showHosters():
    """Folgenbloecke der Detailseite.

    Die eigentlichen Links liegen nicht im Seitenquelltext, sondern werden
    per AJAX nachgeladen; der Parameter dafuer steht base64-kodiert im
    data-enc-Attribut des jeweiligen Blocks. Hier werden diese Parameter
    eingesammelt und in getHosterUrl() abgerufen.
    """
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    if not sHtmlContent:
        return hosters

    isMatch, aResult = cParser.parse(sHtmlContent, r'data-enc="([^"]+)"')
    if not isMatch:
        logger.info('-> [%s]: keine Folgenbloecke gefunden: %s' % (SITE_NAME, sUrl))
        return hosters

    seen = set()
    for sEnc in aResult:
        if sEnc in seen:
            continue
        seen.add(sEnc)
        try:
            aParams = json.loads(base64.b64decode(sEnc).decode('utf-8'))
        except Exception:
            continue
        if not isinstance(aParams, list) or len(aParams) < 5:
            continue
        # Aufbau: ["media", <slug>, "downloads", <staffel>, <index|"cnl">]
        sIndex = aParams[4]
        if sIndex == 'cnl':
            continue  # Click'n'Load-Block, hinter Captcha, kein Stream
        sLabel = 'Folge %s' % (int(sIndex) + 1) if isinstance(sIndex, int) else str(sIndex)
        hosters.append({'link': sEnc, 'name': SITE_NAME,
                        'displayedName': '%s [I]%s[/I]' % (SITE_NAME, sLabel)})
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    """Holt die Links eines Folgenblocks ueber den AJAX-Endpunkt.

    Der Endpunkt erwartet den unveraenderten data-enc-Wert. Schlaegt das
    fehl, wird das protokolliert statt still eine leere Liste zu liefern -
    die Seite aendert ihre AJAX-Schnittstelle erfahrungsgemaess oefter.
    """
    if not sUrl:
        return []
    sContent = cRequestHandler(URL_AJAX + sUrl, caching=False, ignoreErrors=True).request()
    if not sContent:
        logger.info('-> [%s]: AJAX-Abruf ohne Antwort (Sperre oder geaenderte '
                    'Schnittstelle): %s' % (SITE_NAME, sUrl))
        return []
    # Die Antwort enthaelt die Hoster-Adressen als gewoehnliche Links.
    isMatch, aResult = cParser.parse(sContent, r'href="(https?://[^"]+)"')
    if not isMatch:
        logger.info('-> [%s]: AJAX-Antwort ohne Links: %s' % (SITE_NAME, sUrl))
        return []
    for sLink in aResult:
        if DOMAIN not in sLink:
            return [{'streamUrl': sLink, 'resolved': False}]
    return []


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
