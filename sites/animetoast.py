# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showEntries: 3 Stunden
#
# Portiert aus dem CloudStream-Provider AnimeToast.kt (Kotlin).
# Die Uebersicht laeuft ueber die WordPress-REST-API, die Hoster stecken
# hinter einer zweistufigen Verweiskette auf der Detailseite.

import html
import json

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'animetoast'
SITE_NAME = 'Anime Toast'
SITE_ICON = 'animetoast.png'

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'www.animetoast.cc')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_API = URL_MAIN + '/wp-json/wp/v2'
URL_POSTS = URL_API + '/posts?per_page=30&_embed=wp:featuredmedia&page=%s'
URL_CATEGORY = URL_API + '/posts?categories=%s&per_page=30&_embed=wp:featuredmedia&page=%s'
URL_CATEGORIES = URL_API + '/categories?per_page=40'
URL_SEARCH = URL_API + '/search?search=%s&per_page=30'

# Der Player-Verweis zeigt teils auf eine weitere Seite derselben Domain,
# bevor der eigentliche Hoster kommt. Mehr als zwei Spruenge gibt es nicht.
MAX_HOPS = 2


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_POSTS % 1)
    params.setParam('page', '1')
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30500), SITE_IDENTIFIER, 'showEntries'), params)  # Neues
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30506), SITE_IDENTIFIER, 'showGenre'))  # Genre
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def _getJson(sUrl, sGui=False, cacheTime=0):
    oRequest = cRequestHandler(sUrl, ignoreErrors=(sGui is not False))
    if cacheTime:
        oRequest.cacheTime = cacheTime
    sContent = oRequest.request()
    if not sContent:
        return []
    try:
        return json.loads(sContent)
    except ValueError:
        logger.info('-> [%s]: Antwort war kein gueltiges JSON: %s' % (SITE_NAME, sUrl))
        return []


def showGenre():
    """Die WordPress-Kategorien als Menue (Ger Dub, Ger Sub, Movie, ...)."""
    aCategories = _getJson(URL_CATEGORIES, cacheTime=60 * 60 * 48)
    if not isinstance(aCategories, list) or not aCategories:
        cGui().showInfo()
        return
    params = ParameterHandler()
    # Gleichnamige Kategorien zusammenfassen - die Seite fuehrt "Serie" und
    # "Movie" doppelt, mit getrennten Kennungen fuer Dub und Sub.
    merged = {}
    for category in aCategories:
        sName = category.get('name')
        iId = category.get('id')
        if not sName or not iId:
            continue
        merged.setdefault(sName, []).append(str(iId))
    for sName in sorted(merged):
        params.setParam('sCatId', ','.join(merged[sName]))
        params.setParam('page', '1')
        cGui().addFolder(cGuiElement(sName, SITE_IDENTIFIER, 'showEntries'), params)
    cGui().setEndOfDirectory()


def _posterFromPost(post):
    """Beitragsbild aus der eingebetteten Medienangabe, sonst aus dem Text."""
    embedded = (post.get('_embedded') or {}).get('wp:featuredmedia') or []
    for media in embedded:
        if isinstance(media, dict) and media.get('source_url'):
            return media['source_url']
    sContent = ((post.get('content') or {}).get('rendered')) or ''
    isMatch, sImage = cParser.parseSingleResult(sContent, r'<img[^>]+src="([^"]+)"')
    return sImage if isMatch else ''


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    iPage = params.getValue('page')
    iPage = int(iPage) if isinstance(iPage, str) and iPage.isdigit() else 1

    if not entryUrl:
        sCatId = params.getValue('sCatId')
        entryUrl = (URL_CATEGORY % (sCatId, iPage)) if sCatId else (URL_POSTS % iPage)

    cacheTime = 0
    if cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, False):
        cacheTime = 60 * 60 * 3  # 3 Stunden
    aResults = _getJson(entryUrl, sGui, cacheTime)
    if not isinstance(aResults, list) or not aResults:
        if not sGui:
            oGui.showInfo()
        return

    total = len(aResults)
    for post in aResults:
        # Die Suche liefert ein flaches Objekt, posts ein verschachteltes.
        sName = post.get('title')
        if isinstance(sName, dict):
            sName = sName.get('rendered')
        sUrl = post.get('link') or post.get('url')
        if not sName or not sUrl:
            continue
        # Titel aus der REST-API sind HTML-kodiert ("Re&#8217;Zero").
        sName = html.unescape(sName).strip()
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('tvshow')
        sPoster = _posterFromPost(post)
        if sPoster:
            oGuiElement.setThumbnail(sPoster)
        sDate = post.get('date') or ''
        if len(sDate) >= 4 and sDate[:4].isdigit():
            oGuiElement.setYear(sDate[:4])
        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sName)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        # Die REST-API liefert genau per_page Eintraege, solange es weitergeht.
        if total >= 30:
            params.setParam('page', str(iPage + 1))
            oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('tvshows')
        oGui.setEndOfDirectory()


def showHosters():
    """Die Reiter der Detailseite sind die Hoster, darin die Folgenblöcke."""
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    if not sHtmlContent:
        return hosters

    # Reiterbeschriftung je Block: <a data-toggle="tab" href="#multi_link_tabN">Voe</a>
    names = {}
    isMatch, aTabs = cParser.parse(
        sHtmlContent, r'data-toggle="tab"\s+href="#(multi_link_tab\d+)"[^>]*>([^<]+)<')
    if isMatch:
        for sTabId, sLabel in aTabs:
            names[sTabId] = sLabel.strip()

    # Bloecke mit den Folgenverweisen
    isMatch, aBlocks = cParser.parse(
        sHtmlContent, r'id="(multi_link_tab\d+)"[^>]*>(.*?)</div>')
    if not isMatch:
        return hosters
    for sTabId, sBlock in aBlocks:
        sHoster = names.get(sTabId, 'Stream')
        isLink, aLinks = cParser.parse(sBlock, r'href="([^"]+)"[^>]*>(?:<i[^>]*></i>)?\s*([^<]*)<')
        if not isLink:
            continue
        for sLink, sLabel in aLinks:
            sLabel = sLabel.strip() or sHoster
            hosters.append({'link': sLink, 'name': sHoster,
                            'displayedName': '%s [I]%s[/I]' % (sHoster, sLabel)})
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    """Folgt der Verweiskette bis zur eigentlichen Hoster-Adresse."""
    sTarget = sUrl
    for _ in range(MAX_HOPS):
        sHtmlContent = cRequestHandler(sTarget, caching=False).request()
        if not sHtmlContent:
            return []
        isMatch, sNext = cParser.parseSingleResult(
            sHtmlContent, r'id="player-embed"[^>]*>\s*<a[^>]+href="([^"]+)"')
        if not isMatch:
            isMatch, sNext = cParser.parseSingleResult(
                sHtmlContent, r'<iframe[^>]+src="([^"]+)"')
        if not isMatch:
            logger.info('-> [%s]: keine Einbettung gefunden: %s' % (SITE_NAME, sTarget))
            return []
        if sNext.startswith('//'):
            sNext = 'https:' + sNext
        # Zeigt der Verweis noch auf die Seite selbst, einmal weiterspringen.
        if DOMAIN not in sNext:
            return [{'streamUrl': sNext, 'resolved': False}]
        sTarget = sNext
    logger.info('-> [%s]: Verweiskette zu lang: %s' % (SITE_NAME, sUrl))
    return []


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
