# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showEntries: 3 Stunden
#
# Portiert aus dem CloudStream-Provider KinoKing.kt (Kotlin).
# Die Uebersichtsseiten liefern ihre Eintraege als data-Attribute, die
# Hoster stecken hinter je einer Unterseite mit einem iframe.

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'kinoking'
SITE_NAME = 'KinoKing'
SITE_ICON = 'kinoking.png'

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'kinoking.cc')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_INDEX = URL_MAIN + '/index.php'
URL_SEARCH = URL_INDEX + '?search=%s'

# Ein Eintrag traegt vier data-Attribute. Zwischen ihnen koennen weitere
# stehen (data-tmdb, data-quality), deshalb [^>]*? statt \s* - ein striktes
# Muster fand nur 28 der 44 Eintraege.
ITEM_PATTERN = (r'data-id="(\d+)"[^>]*?data-type="([^"]+)"[^>]*?'
                r'data-title="([^"]*)"[^>]*?data-img="([^"]*)"')


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_INDEX)
    params.setParam('sType', 'movie')
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30502), SITE_IDENTIFIER, 'showEntries'), params)  # Filme
    params.setParam('sType', 'series')
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30511), SITE_IDENTIFIER, 'showEntries'), params)  # Serien
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')
    # Bei der Suche steht beides gemischt in einer Liste.
    sType = '' if sSearchText else params.getValue('sType')

    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, False):
        oRequest.cacheTime = 60 * 60 * 3  # 3 Stunden
    sHtmlContent = oRequest.request()
    isMatch, aResult = cParser.parse(sHtmlContent, ITEM_PATTERN)
    if not isMatch:
        if not sGui:
            oGui.showInfo()
        return

    # Die Startseite fuehrt denselben Titel mehrfach (Slider und Raster).
    seen = set()
    entries = []
    for sId, sKind, sName, sImage in aResult:
        if sType and sKind != sType:
            continue
        if not sName or (sId, sKind) in seen:
            continue
        seen.add((sId, sKind))
        entries.append((sId, sKind, sName, sImage))

    if not entries:
        if not sGui:
            oGui.showInfo()
        return

    total = len(entries)
    for sId, sKind, sName, sImage in entries:
        isTvshow = sKind == 'series'
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('tvshow' if isTvshow else 'movie')
        if sImage:
            oGuiElement.setThumbnail(sImage)
        params.setParam('entryUrl', '%s/%s.php?id=%s' % (URL_MAIN, sKind, sId))
        params.setParam('sName', sName)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        oGui.setView('tvshows' if sType == 'series' else 'movies')
        oGui.setEndOfDirectory()


def showHosters():
    """Die Hoster stehen als Unterseiten-Verweise auf der Detailseite.

    Die Einbettung wird bewusst nicht hier aufgeloest: das waere ein
    zusaetzlicher Abruf je Hoster und damit je Aufruf ein Dutzend Anfragen.
    getHosterUrl() holt stattdessen nur die tatsaechlich gewaehlte Seite.
    """
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    isMatch, aResult = cParser.parse(sHtmlContent, r'href="(\?id=[^"]+)"')
    if not isMatch:
        return hosters
    sBase = sUrl.split('?')[0]
    seen = set()
    for sQuery in aResult:
        if sQuery in seen:
            continue
        seen.add(sQuery)
        # Der link-Parameter ist der sprechende Teil, z. B. "cinesrc_backup".
        isName, sLabel = cParser.parseSingleResult(sQuery, r'link=([^&]+)')
        sName = sLabel.replace('_', ' ') if isName else 'Stream'
        hosters.append({'link': sBase + sQuery, 'name': sName,
                        'displayedName': sName})
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    isMatch, sEmbed = cParser.parseSingleResult(sHtmlContent, r'<iframe[^>]+src="([^"]+)"')
    if not isMatch:
        logger.info('-> [%s]: keine Einbettung gefunden: %s' % (SITE_NAME, sUrl))
        return []
    if sEmbed.startswith('//'):
        sEmbed = 'https:' + sEmbed
    # Die Einbettung zeigt auf einen Hoster, den ResolveURL aufloest.
    return [{'streamUrl': sEmbed, 'resolved': False}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
