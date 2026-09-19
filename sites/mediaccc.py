# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# menuCollections: 48 Stunden
# showEntries:      6 Stunden
#
# Portiert aus dem CloudStream-Provider C3TV/MediaCCC.kt (Kotlin).
# Quelle ist die offene, dokumentierte JSON-API von media.ccc.de - es gibt
# keine Hoster-Kette, die Aufnahmen liegen als direkte Dateien vor.

import json

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'mediaccc'
SITE_NAME = 'media.ccc.de'
SITE_ICON = 'mediaccc.png'

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'api.media.ccc.de')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_RECENT = URL_MAIN + '/public/events/recent'
URL_CONFERENCES = URL_MAIN + '/public/conferences'
URL_SEARCH = URL_MAIN + '/public/events/search?q=%s'


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_RECENT)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30500), SITE_IDENTIFIER, 'showEntries'), params)  # Neu
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30543), SITE_IDENTIFIER, 'menuCollections'))  # Kollektionen
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def _getJson(sUrl, sGui=False, cacheTime=0):
    """Holt und dekodiert eine API-Antwort. Liefert {} statt zu werfen."""
    oRequest = cRequestHandler(sUrl, ignoreErrors=(sGui is not False))
    if cacheTime:
        oRequest.cacheTime = cacheTime
    sContent = oRequest.request()
    if not sContent:
        return {}
    try:
        return json.loads(sContent)
    except ValueError:
        logger.info('-> [%s]: Antwort war kein gueltiges JSON: %s' % (SITE_NAME, sUrl))
        return {}


def menuCollections():
    """Konferenzen als Ordnerliste. Die API liefert sie in einem Rutsch."""
    jData = _getJson(URL_CONFERENCES, cacheTime=60 * 60 * 48)  # 48 Stunden
    aConferences = jData.get('conferences') or []
    if not aConferences:
        cGui().showInfo()
        return
    params = ParameterHandler()
    total = len(aConferences)
    # Neueste Konferenz zuerst - die API sortiert aufsteigend.
    for conference in reversed(aConferences):
        sTitle = conference.get('title')
        sUrl = conference.get('url')
        if not sTitle or not sUrl:
            continue
        oGuiElement = cGuiElement(sTitle, SITE_IDENTIFIER, 'showCollections')
        sLogo = conference.get('logo_url')
        if sLogo:
            oGuiElement.setThumbnail(sLogo)
        params.setParam('sUrl', sUrl)
        cGui().addFolder(oGuiElement, params, True, total)
    cGui().setEndOfDirectory()


def showCollections():
    """Vortraege einer einzelnen Konferenz."""
    sUrl = ParameterHandler().getValue('sUrl')
    if not sUrl:
        cGui().showInfo()
        return
    _listEvents(_getJson(sUrl, cacheTime=60 * 60 * 6).get('events') or [])


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')
    cacheTime = 0
    if cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, False):
        cacheTime = 60 * 60 * 6  # 6 Stunden
    aEvents = _getJson(entryUrl, sGui, cacheTime).get('events') or []
    _listEvents(aEvents, oGui, sGui)


def _listEvents(aEvents, oGui=None, sGui=False):
    """Baut die Liste der Vortraege. Gemeinsam fuer Neu, Konferenz und Suche."""
    if oGui is None:
        oGui = cGui()
    if not aEvents:
        if not sGui:
            oGui.showInfo()
        return

    params = ParameterHandler()
    # Filter nach eingestellter Sprache in gerxstream laden
    sLanguage = cConfig().getSetting('prefLanguage')
    total = len(aEvents)

    for event in aEvents:
        sName = event.get('title')
        sUrl = event.get('url')
        if not sName or not sUrl:
            continue

        # media.ccc.de liefert ISO-639-2 ('deu', 'eng'), teils mehrsprachig.
        sLang = (event.get('original_language') or '').lower()
        if sLanguage == '1' and sLang and 'deu' not in sLang:  # nur Deutsch
            continue
        if sLanguage == '2' and sLang and 'eng' not in sLang:  # nur Englisch
            continue

        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        if sLang:
            oGuiElement.setLanguage(sLang)
        sSubtitle = event.get('subtitle')
        sDesc = event.get('description')
        if sSubtitle and sDesc:
            oGuiElement.setDescription('%s\n\n%s' % (sSubtitle, sDesc))
        elif sDesc or sSubtitle:
            oGuiElement.setDescription(sDesc or sSubtitle)
        sThumb = event.get('poster_url') or event.get('thumb_url')
        if sThumb:
            oGuiElement.setThumbnail(sThumb)
        sDate = event.get('date') or ''
        if len(sDate) >= 4 and sDate[:4].isdigit():
            oGuiElement.setYear(sDate[:4])
        oGuiElement.setMediaType('movie')

        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sName)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showHosters():
    """Die Aufnahmen eines Vortrags. Direkte Dateien, kein Resolver noetig."""
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    jEvent = _getJson(sUrl)
    for recording in jEvent.get('recordings') or []:
        sMime = recording.get('mime_type') or ''
        sLink = recording.get('recording_url')
        if not sLink or not sMime.startswith('video'):
            continue  # Untertitelspuren (text/*) hier ueberspringen
        sQuality = str(recording.get('height') or '')
        sLang = recording.get('language') or ''
        sName = cParser.urlparse(sLink)
        sDisplayed = '%s [I]%s' % (sName, sLang)
        if sQuality:
            sDisplayed += ' [%sp]' % sQuality
        sDisplayed += '[/I]'
        hoster = {'link': sLink, 'name': sName, 'displayedName': sDisplayed}
        if sQuality:
            hoster['quality'] = sQuality
        hosters.append(hoster)
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    # media.ccc.de liefert fertige mp4/webm-Adressen, ResolveURL wird nicht
    # gebraucht - deshalb resolved=True.
    return [{'streamUrl': sUrl, 'resolved': True}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
