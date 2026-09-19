# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showGenre:    12 Stunden
# showEntries:   3 Stunden
#
# Portiert aus dem CloudStream-Provider ARD.kt (Kotlin).
# Oeffentlich-rechtliche Mediathek mit offener JSON-API, keine Hoster-Kette:
# die Beitraege liegen als direkte mp4- bzw. HLS-Adressen vor.

import json

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'ardmediathek'
SITE_NAME = 'ARD Mediathek'
SITE_ICON = 'ardmediathek.png'

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'api.ardmediathek.de')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_PAGE = URL_MAIN + '/page-gateway/pages/ard/%s?embedded=false'
URL_ITEM = URL_MAIN + '/page-gateway/pages/ard/item/%s?embedded=true&mcV6=true'
URL_SEARCH = (URL_MAIN + '/search-system/search/vods/ard'
              '?query=%s&pageSize=50&platform=MEDIA_THEK&sortingCriteria=SCORE_DESC')

# Redaktionelle Seiten der Mediathek. Der Name ist zugleich der Menuepunkt.
SECTIONS = (
    ('Startseite', 'home'),
    ('Filme', 'editorial/filme'),
    ('Serien', 'editorial/serien'),
    ('Dokus', 'editorial/dokus'),
    ('Geschichte', 'editorial/geschichte'),
    ('Investigativ', 'editorial/investigativ'),
)

# Bildadressen enthalten einen {width}-Platzhalter.
IMAGE_WIDTH = '1920'
THUMB_WIDTH = '640'


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    for title, path in SECTIONS:
        params.setParam('sUrl', URL_PAGE % path)
        cGui().addFolder(cGuiElement(title, SITE_IDENTIFIER, 'showGenre'), params)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def _getJson(sUrl, sGui=False, cacheTime=0):
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


def _image(images, width):
    """Bildadresse aus dem images-Objekt; {width} wird ersetzt."""
    if not isinstance(images, dict):
        return ''
    for key in ('aspect16x9', 'aspect3x2', 'aspect1x1'):
        entry = images.get(key)
        if isinstance(entry, dict) and entry.get('src'):
            return entry['src'].replace('{width}', width)
    for entry in images.values():
        if isinstance(entry, dict) and entry.get('src'):
            return entry['src'].replace('{width}', width)
    return ''


def showGenre():
    """Die Rubriken einer redaktionellen Seite. Sie sind die Kategorien."""
    sUrl = ParameterHandler().getValue('sUrl')
    if not sUrl:
        cGui().showInfo()
        return
    jData = _getJson(sUrl, cacheTime=60 * 60 * 12)  # 12 Stunden
    aWidgets = jData.get('widgets') or []
    params = ParameterHandler()
    total = 0
    for widget in aWidgets:
        # Die Navigationsleiste ist keine Inhaltsrubrik.
        if widget.get('type') == 'top_navigation':
            continue
        sTitle = widget.get('title')
        sHref = ((widget.get('links') or {}).get('self') or {}).get('href')
        if not sTitle or not sHref:
            continue
        params.setParam('sUrl', sHref)
        cGui().addFolder(cGuiElement(sTitle, SITE_IDENTIFIER, 'showEntries'), params)
        total += 1
    if not total:
        cGui().showInfo()
        return
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')
    cacheTime = 0
    if cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, False):
        cacheTime = 60 * 60 * 3  # 3 Stunden
    jData = _getJson(entryUrl, sGui, cacheTime)

    # Rubrik und Suche liefern die Teaser an unterschiedlicher Stelle.
    aTeasers = jData.get('teasers') or []
    if not aTeasers:
        for widget in jData.get('widgets') or []:
            aTeasers.extend(widget.get('teasers') or [])

    if not aTeasers:
        if not sGui:
            oGui.showInfo()
        return

    total = len(aTeasers)
    for teaser in aTeasers:
        sName = (teaser.get('shortTitle') or teaser.get('mediumTitle')
                 or teaser.get('longTitle'))
        sId = ((teaser.get('links') or {}).get('target') or {}).get('id') or teaser.get('id')
        if not sName or not sId:
            continue
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('movie')
        sShow = teaser.get('show')
        if isinstance(sShow, dict):
            sShow = sShow.get('title')
        if sShow and sShow != sName:
            oGuiElement.setTitleSecond(sShow)
        sThumb = _image(teaser.get('images'), THUMB_WIDTH)
        if sThumb:
            oGuiElement.setThumbnail(sThumb)
        sBroadcast = teaser.get('broadcastedOn') or ''
        if len(sBroadcast) >= 4 and sBroadcast[:4].isdigit():
            oGuiElement.setYear(sBroadcast[:4])
        params.setParam('entryUrl', URL_ITEM % sId)
        params.setParam('sName', sName)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showHosters():
    """Die Streams eines Beitrags. Direkte Adressen, kein Resolver noetig."""
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    jItem = _getJson(sUrl)
    seen = set()
    for widget in jItem.get('widgets') or []:
        embedded = (widget.get('mediaCollection') or {}).get('embedded') or {}
        for stream in embedded.get('streams') or []:
            for media in stream.get('media') or []:
                sLink = media.get('url')
                if not sLink or sLink in seen:
                    continue
                seen.add(sLink)
                sMime = media.get('mimeType') or ''
                sQuality = str(media.get('maxHResolutionPx') or '')
                sName = cParser.urlparse(sLink)
                sKind = 'HLS' if 'mpegurl' in sMime else 'MP4'
                sDisplayed = '%s [I]%s' % (sName, sKind)
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
    # Die ARD liefert fertige mp4- und HLS-Adressen, ResolveURL entfaellt.
    return [{'streamUrl': sUrl, 'resolved': True}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
