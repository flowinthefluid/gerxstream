# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
#
# Flixitv-Stream.eu - Bootstrap-basierte Linklist-Seite mit Filmen und
# Serien in einer gemeinsamen, unpaginierten Katalogseite (/serie). Jeder
# Eintrag - auch ein Einzelfilm - haengt an einer "Staffelauswahl" mit
# mindestens einer Staffel, darunter eine Episodentabelle. Die Wiedergabe-
# seite bindet neben dem echten Hoster (hubu.cloud) noch einen Werbe-Iframe
# ein, der bewusst uebersprungen wird (Beschraenkung auf den "ifc"-Container).

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'flixitvstream'
SITE_NAME = 'Flixitv-Stream.eu'
SITE_ICON = 'flixitvstream.png'
CONTENT_CATEGORIES = ('filme', 'serien')

if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'flixitv-stream.eu')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_LIST = URL_MAIN + '/serie'

ENTRY_PATTERN = (r'<a href="([^"]+)" class="text-decoration-none"><div class="card h-100">'
                r'<img src="([^"]+)" class="card-img-top" alt="([^"]+)">'
                r'<div class="card-body"><h5 class="card-title">[^<]+</h5>'
                r'<p class="card-text">\xb7\s*([^<]+)</p>')
SEASON_PATTERN = (r'<a href="(\?v=[^"]+&s=\d+)" class="card-link"><div class="card">'
                r'<img src="[^"]*" class="card-img-top" alt="[^"]*">'
                r'<div class="card-info"><h5>([^<]+)</h5>')
EPISODE_PATTERN = (r'<tr><td><a href="(/watch\?v=[^"]+)"><img[^>]*></a></td>'
                r'<td><a href="[^"]+" class="link-light">([^<]*)</a></td>'
                r'<td><a href="[^"]+" class="link-light">([^<]*)</a></td></tr>')


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_LIST)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30502), SITE_IDENTIFIER, 'showEntries'), params)  # Filme & Serien
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')
    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    sHtmlContent = oRequest.request()
    isMatch, aResult = cParser.parse(sHtmlContent, ENTRY_PATTERN)
    if not isMatch:
        if not sGui:
            oGui.showInfo()
        return

    total = len(aResult)
    for sUrl, sThumbnail, sName, sKind in aResult:
        if sSearchText and not cParser.search(sSearchText, sName):
            continue
        isTvshow = 'folge' in sKind.lower()
        if sUrl.startswith('/'):
            sUrl = URL_MAIN + sUrl
        if sThumbnail.startswith('/'):
            sThumbnail = URL_MAIN + sThumbnail
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showSeasons')
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setMediaType('tvshow' if isTvshow else 'movie')
        params.setParam('entryUrl', sUrl)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        oGui.setView('tvshows')
        oGui.setEndOfDirectory()


def showSeasons(entryUrl=False):
    oGui = cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('entryUrl')
    sHtmlContent = cRequestHandler(entryUrl).request()
    isMatch, aResult = cParser.parse(sHtmlContent, SEASON_PATTERN)
    if not isMatch:
        oGui.showInfo()
        return

    # Der Grundpfad fuer relative Staffel-Links ist immer /serie.
    sBase = URL_MAIN + '/serie'
    if len(aResult) == 1:
        # Auch Einzelfilme haben formal eine "Staffel 1" - dem Nutzer
        # bleibt der zusaetzliche Klick auf eine einzige Staffel erspart.
        sHref, sName = aResult[0]
        showEpisodes(sBase + sHref)
        return

    total = len(aResult)
    for sHref, sName in aResult:
        params.setParam('seasonUrl', sBase + sHref)
        oGui.addFolder(cGuiElement(sName, SITE_IDENTIFIER, 'showEpisodes'), params, False, total)
    oGui.setEndOfDirectory()


def showEpisodes(seasonUrl=False):
    oGui = cGui()
    params = ParameterHandler()
    if not seasonUrl:
        seasonUrl = params.getValue('seasonUrl')
    sHtmlContent = cRequestHandler(seasonUrl).request()
    isMatch, aResult = cParser.parse(sHtmlContent, EPISODE_PATTERN)
    if not isMatch:
        oGui.showInfo()
        return

    total = len(aResult)
    for sUrl, sNumber, sTitle in aResult:
        sName = '%s. %s' % (sNumber, sTitle) if sTitle else sNumber
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('episode')
        if sUrl.startswith('/'):
            sUrl = URL_MAIN + sUrl
        params.setParam('entryUrl', sUrl)
        oGui.addFolder(oGuiElement, params, False, total)
    oGui.setEndOfDirectory()


def showHosters():
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    isMatch, sContainer = cParser.parseSingleResult(sHtmlContent, r'class="ifc">([\s\S]{0,1000})')
    if not isMatch:
        sContainer = sHtmlContent
    isMatch, sEmbed = cParser.parseSingleResult(sContainer, r'<iframe src="([^"]+)"')
    if isMatch:
        hosters.append({'link': sEmbed, 'name': cParser.urlparse(sEmbed)})
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
    showEntries(URL_LIST, oGui, sSearchText)
