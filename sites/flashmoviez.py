# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
#
# Flash-Moviez.Tv (flash-moviez.ucoz.org) - uCoz-basierte Linklist-Seite mit
# 25 Genres (u.a. eine eigene "Dokus / Shows"-Kategorie). Die Eintraege
# verlinken auf bekannte Hoster (streamcloud.eu, divxstage, movshare, ...),
# die von der zentralen Hoster-Aufloesung des Addons behandelt werden.
# Die Seite bindet zusaetzlich einen YouTube-Trailer und Werbe-Iframes auf
# der Detailseite ein - beide werden bewusst uebersprungen.

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'flashmoviez'
SITE_NAME = 'Flash-Moviez.Tv'
SITE_ICON = 'flashmoviez.png'
CONTENT_CATEGORIES = ('filme', 'serien')

if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'flash-moviez.ucoz.org')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_SEARCH = URL_MAIN + '/search/?q=%s'


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30506), SITE_IDENTIFIER, 'showGenre'))  # Genre
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def showGenre():
    params = ParameterHandler()
    sHtmlContent = cRequestHandler(URL_MAIN + '/').request()
    pattern = r'<li><a\s+href="([^"]+)"\s*><span>»\s*([^<]+)</span></a></li>'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        cGui().showInfo()
        return

    for sUrl, sName in aResult:
        params.setParam('sUrl', sUrl)
        cGui().addFolder(cGuiElement(sName.strip(), SITE_IDENTIFIER, 'showEntries'), params)
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')
    iPage = int(params.getValue('page'))
    sPageUrl = entryUrl + '-' + str(iPage) if iPage > 1 else entryUrl
    oRequest = cRequestHandler(sPageUrl, ignoreErrors=(sGui is not False))
    sHtmlContent = oRequest.request()
    pattern = r'<h4 class="viewn_title" align="center"><a href="([^"]+)">([^<]+)</a>.*?<img src="([^"]+)"'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        if not sGui:
            oGui.showInfo()
        return

    total = len(aResult)
    for sUrl, sName, sThumbnail in aResult:
        if sSearchText and not cParser.search(sSearchText, sName):
            continue
        if sUrl.startswith('/'):
            sUrl = URL_MAIN + sUrl
        if sThumbnail.startswith('/'):
            sThumbnail = URL_MAIN + sThumbnail
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setMediaType('movie')
        params.setParam('entryUrl', sUrl)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui and not sSearchText:
        sPageNr = int(params.getValue('page'))
        sPageNr = 2 if sPageNr == 0 else sPageNr + 1
        params.setParam('page', int(sPageNr))
        params.setParam('sUrl', entryUrl)
        oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showHosters():
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    isMatch, sContainer = cParser.parseSingleResult(sHtmlContent, r'class="eText"[^>]*>([\s\S]+?)<!-- </body> -->')
    if not isMatch:
        sContainer = sHtmlContent
    isMatch, aResult = cParser.parse(sContainer, r'<a target="_blank" href="\s*([^"\s]+)\s*">')
    if isMatch:
        for sHosterUrl in aResult:
            if 'youtube' in sHosterUrl:
                continue
            hoster = {'link': sHosterUrl, 'name': cParser.urlparse(sHosterUrl)}
            hosters.append(hoster)
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    return [{'streamUrl': sUrl, 'resolved': False}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30289))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
