# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showEntries: 3 Stunden
#
# anime-stream.to steht hinter Cloudflare (echte JS-Challenge, nicht nur ein
# 403 aus anderem Grund - siehe resources/lib/handler/protection.py) und
# laedt Episoden clientseitig ueber eine zweistufige, tokenbasierte AJAX-API.
#
# Aufbau, an einem Archiv-Schnappschuss (Wayback Machine, Dez. 2025 / Jan.
# 2026) verifiziert:
#   Uebersicht  <a href="/anime-serien/<slug>" class="panel-link">
#               <Titel> <span class="year">(<Jahr>)</span></a> ... <img src=
#               24 von 24 Kacheln auf /alle-serien trafen dieses Muster.
#   Detailseite eigenes JavaScript der Seite (nicht erraten, wortwoertlich
#               aus einem archivierten <script>-Block):
#                 1. GET /generate_token.php?serie_id=<id>&season=<n>
#                    -> {"success": true, "token": "..."}
#                 2. GET /includes/ajax/load_episodes.php?serie_id=<id>
#                    &season=<n>&token=<token>
#                    -> {"html": "<Markup der Episodenliste>"}
#
# Der zweite Schritt selbst - Form des zurueckgelieferten HTML - konnte von
# hier aus nicht gegengeprueft werden, weil Cloudflare den direkten Zugriff
# blockiert. getEpisodesForSeason() sucht deshalb bewusst allgemein nach
# Hoster-Verweisen (iframe/data-src auf eine fremde Domain) statt nach einer
# erratenen, moeglicherweise falschen Klassenstruktur, und protokolliert
# ausdruecklich, wenn nichts gefunden wird.

import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'animestream'
SITE_NAME = 'Anime-Stream'
SITE_ICON = 'animestream.png'
CONTENT_CATEGORIES = ('animes',)

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'anime-stream.to')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_SERIES = URL_MAIN + '/alle-serien'
URL_MOVIES = URL_MAIN + '/alle-filme'
URL_SEARCH = URL_MAIN + '/search.php?q=%s'
URL_TOKEN = URL_MAIN + '/generate_token.php?serie_id=%s&season=%s'
URL_EPISODES = URL_MAIN + '/includes/ajax/load_episodes.php?serie_id=%s&season=%s&token=%s'

ITEM_PATTERN = (r'<a href="(/anime-(?:serien|filme)/[^"]+)" class="panel-link">\s*'
                r'([^<]+?)\s*<span class="year">\(([^)]*)\)</span>.*?'
                r'<img src="([^"]+)"')
SEARCH_PATTERN = (r'<div class="search-result-item">.*?'
                  r'<a href="(/anime-(?:serien|filme)/[^"]+)">\s*'
                  r'<img src="([^"]+)".*?<h3>\s*'
                  r'<a href="[^"]+">\s*([^<]+?)\s*</a>')
PAGE_PATTERN = r'<span class="page-info">\s*(\d+)\s*/\s*(\d+)\s*</span>'
SERIES_ID_PATTERN = r'const\s+seriesId\s*=\s*(\d+)\s*;'
SEASON_BLOCK_PATTERN = r'id="season-(\d+)"'


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_SERIES)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30511), SITE_IDENTIFIER, 'showEntries'), params)  # Serien
    params.setParam('sUrl', URL_MOVIES)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30502), SITE_IDENTIFIER, 'showEntries'), params)  # Filme
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def _pageUrl(url, page):
    """Ersetzt nur den page-Parameter und behaelt alle anderen bei."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query['page'] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(query), parts.fragment))


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
        # Bei aktiver Cloudflare-Sperre hat der requestHandler bereits ueber
        # protection.notifyOnce() auf die Bot-Schutz-Einstellungen
        # hingewiesen; hier waere eine zweite Meldung nur Laerm.
        if not sGui:
            oGui.showInfo()
        return

    # Die Suche liefert ein anderes, eigenes Karten-Layout als die
    # Katalogseiten. Der alte /suche-Pfad und das Katalogmuster konnten daher
    # nie Treffer liefern.
    isMatch, aResult = cParser.parse(
        sHtmlContent, SEARCH_PATTERN if sSearchText else ITEM_PATTERN)
    if not isMatch:
        if not sGui:
            oGui.showInfo()
        return

    entries = []
    seen = set()
    for result in aResult:
        if sSearchText:
            sSlug, sImage, sTitle = result
            sYear = ''
        else:
            sSlug, sTitle, sYear, sImage = result
        if sSlug in seen:
            continue
        seen.add(sSlug)
        entries.append((sSlug, sTitle, sYear, sImage))

    total = len(entries)
    for sSlug, sTitle, sYear, sImage in entries:
        sTitle = sTitle.strip()
        oGuiElement = cGuiElement(sTitle, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('tvshow' if '/anime-serien/' in sSlug else 'movie')
        if sImage:
            oGuiElement.setThumbnail(sImage)
        if sYear.strip().isdigit():
            oGuiElement.setYear(sYear.strip())
        params.setParam('entryUrl', URL_MAIN + sSlug)
        params.setParam('sName', sTitle)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        if not sSearchText:
            isPage, aPages = cParser.parse(sHtmlContent, PAGE_PATTERN)
            if isPage:
                current, last = aPages[0]
                if current.isdigit() and last.isdigit() and int(current) < int(last):
                    params.setParam('sUrl', _pageUrl(entryUrl, int(current) + 1))
                    oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('tvshows' if '/alle-serien' in entryUrl else 'movies')
        oGui.setEndOfDirectory()


def _getSeriesId(sHtmlContent):
    isMatch, sId = cParser.parseSingleResult(sHtmlContent, SERIES_ID_PATTERN)
    return sId if isMatch else ''


def _getEpisodesForSeason(sSeriesId, sSeason):
    """Fuehrt den zweistufigen Fluss aus der Seiten-eigenen JS aus.

    Beide Schritte liefern JSON. Schlaegt einer fehl, wird das protokolliert
    statt still eine leere Liste durchzureichen - diese Kette ist
    reverse-engineert und keine Garantie, dass sie unveraendert bleibt.
    """
    sTokenResponse = cRequestHandler(URL_TOKEN % (sSeriesId, sSeason),
                                     caching=False, ignoreErrors=True).request()
    if not sTokenResponse:
        logger.info('-> [%s]: generate_token.php ohne Antwort (Staffel %s)'
                    % (SITE_NAME, sSeason))
        return ''
    try:
        jToken = json.loads(sTokenResponse)
    except ValueError:
        logger.info('-> [%s]: generate_token.php lieferte kein JSON' % SITE_NAME)
        return ''
    if not isinstance(jToken, dict):
        logger.info('-> [%s]: generate_token.php lieferte ein ungueltiges JSON-Objekt' % SITE_NAME)
        return ''
    sToken = jToken.get('token')
    if not jToken.get('success') or not sToken:
        logger.info('-> [%s]: kein Token erhalten: %s' % (SITE_NAME, str(jToken)[:160]))
        return ''

    sEpisodesResponse = cRequestHandler(
        URL_EPISODES % (sSeriesId, sSeason, sToken),
        caching=False, ignoreErrors=True).request()
    if not sEpisodesResponse:
        logger.info('-> [%s]: load_episodes.php ohne Antwort' % SITE_NAME)
        return ''
    try:
        jEpisodes = json.loads(sEpisodesResponse)
    except ValueError:
        logger.info('-> [%s]: load_episodes.php lieferte kein JSON' % SITE_NAME)
        return ''
    return jEpisodes.get('html', '') if isinstance(jEpisodes, dict) else ''


def showHosters():
    """Holt fuer jede erkannte Staffel die Episoden ueber den Token-Fluss.

    Sucht in der zurueckgelieferten Fragment-HTML allgemein nach Verweisen
    auf fremde Domains (iframe- oder data-Attribute) statt nach einer
    erratenen Klasse - die tatsaechliche Markup-Form des Fragments war von
    hier aus nicht pruefbar.
    """
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    if not sHtmlContent:
        return hosters

    sSeriesId = _getSeriesId(sHtmlContent)
    if not sSeriesId:
        logger.info('-> [%s]: seriesId nicht gefunden: %s' % (SITE_NAME, sUrl))
        return hosters

    isMatch, aSeasons = cParser.parse(sHtmlContent, SEASON_BLOCK_PATTERN)
    if not isMatch:
        aSeasons = ['1']  # Filme und einstaffelige Serien haben oft keinen Block.

    for sSeason in sorted(set(aSeasons), key=lambda s: int(s) if s.isdigit() else 0):
        sFragment = _getEpisodesForSeason(sSeriesId, sSeason)
        if not sFragment:
            continue
        isLink, aLinks = cParser.parse(
            sFragment, r'(?:iframe[^>]+src|data-src|data-url)="(https?://(?!%s)[^"]+)"' % re.escape(DOMAIN))
        if not isLink:
            continue
        for sLink in aLinks:
            sName = cParser.urlparse(sLink)
            hosters.append({'link': sLink, 'name': sName,
                            'displayedName': '%s [I]Staffel %s[/I]' % (sName, sSeason)})

    if hosters:
        hosters.append('getHosterUrl')
    else:
        logger.info('-> [%s]: keine Hoster-Links im Episoden-Fragment gefunden: %s'
                    % (SITE_NAME, sUrl))
    return hosters


def getHosterUrl(sUrl=False):
    if sUrl.startswith('//'):
        sUrl = 'https:' + sUrl
    return [{'streamUrl': sUrl, 'resolved': False}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
