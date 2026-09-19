# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showGenre:    24 Stunden
# showEntries:   3 Stunden
#
# 4anime.com.ro ist englischsprachig, keine deutsche Quelle - aufgenommen auf
# ausdruecklichen Wunsch. WordPress-Theme (animestream-child). Aufbau an
# Live-Daten geprueft:
#   Uebersicht  <a class="series" href="/anime/<slug>/" ...><img src="..."
#               30 Treffer (15 eindeutige Serien, da Bild und Titel je
#               einen eigenen class="series"-Link tragen) auf /anime/.
#   Detailseite Episodenliste in <ul>...<li><a href="<episode-url>"
#               title="Episode N"><div class="epl-num">N</div>...
#               9 von 9 Episoden fuer "Oshi No Ko Season 3" korrekt erkannt.
#   Episode     <iframe src=".../player/?source=blogger&url=<verschluesselt>">
#   Player      Der Player-Endpunkt loest serverseitig auf und liefert im
#               Antwort-HTML ein JS-Array "var sources = [...]" mit fertigen
#               googlevideo.com-Adressen (YouTube-Infrastruktur, ueber
#               "source=blogger" eingebunden). Keine eigene Entschluesselung
#               noetig - live geprueft, das Array enthielt zwei Qualitaeten.
#               Die Adressen sind zeitlich begrenzt (expire=-Parameter),
#               deshalb wird erst in getHosterUrl() aufgeloest.

import html
import json

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'anime4'
SITE_NAME = '4anime'
SITE_ICON = 'anime4.png'

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', '4anime.com.ro')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_LIST = URL_MAIN + '/anime/'
URL_SEARCH = URL_MAIN + '/wp-json/wp/v2/search?search=%s&per_page=30&subtype=anime'

GENRES = (
    'action', 'adventure', 'comedy', 'drama', 'fantasy', 'martial-arts',
    'romance', 'seinen', 'shounen', 'supernatural', 'suspense',
    'award-winning',
)

SHOW_PATTERN = (r'<a class="series" href="(https://%s/anime/[a-z0-9-]+/)"'
                r'[^>]*>\s*<img src="([^"]+)"[^>]*title="([^"]*)"')
EPISODE_PATTERN = (r'<a href="(https://%s/[a-z0-9-]+/)" title="Episode (\d+)">\s*'
                   r'<div class="epl-num">\d+</div>')


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_LIST)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30506), SITE_IDENTIFIER, 'showShows'), params)  # Genre (Sammelmenue darunter)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def showGenre():
    """Menue der Genres; jedes fuehrt zu einer gefilterten Show-Liste."""
    params = ParameterHandler()
    for sGenre in GENRES:
        params.setParam('sUrl', '%s/genres/%s/' % (URL_MAIN, sGenre))
        cGui().addFolder(cGuiElement(sGenre.replace('-', ' ').title(), SITE_IDENTIFIER, 'showShows'), params)
    cGui().setEndOfDirectory()


def showShows(entryUrl=False, sGui=False, sSearchText=False):
    """Zeigt Serien-Kacheln (Uebersicht oder Genre)."""
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')

    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, False):
        oRequest.cacheTime = 60 * 60 * 3  # 3 Stunden
    sHtmlContent = oRequest.request()
    if not sHtmlContent:
        if not sGui:
            oGui.showInfo()
        return

    isMatch, aResult = cParser.parse(sHtmlContent, SHOW_PATTERN % cParser.escape(DOMAIN))
    if not isMatch:
        if not sGui:
            oGui.showInfo()
        return

    # Jede Kachel hat zwei class="series"-Links (Bild und Titel), das
    # Muster trifft deshalb beide - ohne Entdopplung erschiene jede Serie
    # zweimal. Geprueft: 30 Treffer, 15 eindeutige Adressen.
    seen = set()
    entries = []
    for sUrl, sImage, sTitle in aResult:
        if sUrl in seen:
            continue
        seen.add(sUrl)
        entries.append((sUrl, sImage, html.unescape(sTitle).strip()))

    total = len(entries)
    for sUrl, sImage, sTitle in entries:
        oGuiElement = cGuiElement(sTitle, SITE_IDENTIFIER, 'showEntries')
        oGuiElement.setMediaType('tvshow')
        if sImage:
            oGuiElement.setThumbnail(sImage)
        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sTitle)
        oGui.addFolder(oGuiElement, params, True, total)

    if not sGui:
        oGui.setView('tvshows')
        oGui.setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    """Episodenliste einer Serie."""
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('entryUrl') or params.getValue('sUrl')

    sHtmlContent = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False)).request()
    if not sHtmlContent:
        if not sGui:
            oGui.showInfo()
        return

    isMatch, aResult = cParser.parse(sHtmlContent, EPISODE_PATTERN % cParser.escape(DOMAIN))
    if not isMatch:
        if not sGui:
            oGui.showInfo()
        return

    sBaseTitle = params.getValue('sName') or ''
    total = len(aResult)
    for sUrl, sEpisode in sorted(aResult, key=lambda item: int(item[1])):
        sTitle = '%s - Episode %s' % (sBaseTitle, sEpisode) if sBaseTitle else 'Episode %s' % sEpisode
        oGuiElement = cGuiElement(sTitle, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('episode')
        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sTitle)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        oGui.setEndOfDirectory()


def showHosters():
    """Liest den Player-Verweis aus der Episodenseite."""
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    if not sHtmlContent:
        return hosters

    isMatch, sEmbed = cParser.parseSingleResult(
        sHtmlContent, r'<iframe[^>]+src="(https://[^"]+/player/\?[^"]+)"')
    if not isMatch:
        logger.info('-> [%s]: keine Player-Einbettung gefunden: %s' % (SITE_NAME, sUrl))
        return hosters
    hosters.append({'link': sEmbed, 'name': SITE_NAME, 'displayedName': SITE_NAME})
    hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    """Ruft den Player-Endpunkt ab, der die Verschluesselung serverseitig
    aufloest, und liest die fertigen Adressen aus dem eingebetteten
    JW-Player-Skript. Die hoechste Qualitaet steht zuletzt im Array."""
    if not sUrl:
        return []
    sHtmlContent = cRequestHandler(sUrl, caching=False, ignoreErrors=True).request()
    if not sHtmlContent:
        logger.info('-> [%s]: Player-Endpunkt ohne Antwort: %s' % (SITE_NAME, sUrl))
        return []
    isMatch, sSourcesJson = cParser.parseSingleResult(
        sHtmlContent, r'var sources = (\[.*?\]);')
    if not isMatch:
        logger.info('-> [%s]: kein sources-Array im Player: %s' % (SITE_NAME, sUrl))
        return []
    try:
        aSources = json.loads(sSourcesJson)
    except ValueError:
        logger.info('-> [%s]: sources-Array kein gueltiges JSON' % SITE_NAME)
        return []
    streams = []
    for source in aSources:
        sFile = source.get('file') if isinstance(source, dict) else None
        if sFile:
            streams.append({'streamUrl': sFile, 'resolved': True})
    return streams


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    """Sucht ueber die WP-REST-API und leitet direkt in die Episodenliste."""
    oGuiObj = oGui if oGui else cGui()
    sContent = cRequestHandler(URL_SEARCH % cParser.quotePlus(sSearchText),
                               ignoreErrors=(oGui is not False)).request()
    if not sContent:
        return
    try:
        aResults = json.loads(sContent)
    except ValueError:
        return
    if not isinstance(aResults, list):
        return
    params = ParameterHandler()
    total = len(aResults)
    for result in aResults:
        sTitle = result.get('title')
        sUrl = result.get('url')
        if not sTitle or not sUrl:
            continue
        oGuiElement = cGuiElement(sTitle, SITE_IDENTIFIER, 'showEntries')
        oGuiElement.setMediaType('tvshow')
        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sTitle)
        oGuiObj.addFolder(oGuiElement, params, True, total)
