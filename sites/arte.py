# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showGenre:    12 Stunden
# showEntries:   3 Stunden
#
# Portiert aus dem CloudStream-Provider Arte.kt (Kotlin).
# Oeffentlich-rechtlicher Kultursender mit offener JSON-API, keine
# Hoster-Kette: die Beitraege liegen als direkte HLS-Adressen vor.
#
# Hinweis zur Drosselung: api.arte.tv beantwortet zu dichte Abfragen, indem es
# "429 - Too Many Requests" als Text mitten in die JSON-Antwort schreibt,
# statt einen HTTP-Fehler zu liefern. _getJson() faengt das ab, sonst bricht
# die Listenerstellung mit einem Parserfehler ab.

import json

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'arte'
SITE_NAME = 'Arte'
SITE_ICON = 'arte.png'

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'api.arte.tv')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

LANG = 'de'
URL_MAIN = 'https://' + DOMAIN
URL_PAGE = URL_MAIN + '/api/emac/v4/' + LANG + '/web/pages/%s'
URL_SEARCH = URL_MAIN + '/api/emac/v4/' + LANG + '/web/pages/SEARCH/?page=1&query=%s'
URL_PLAYER = URL_MAIN + '/api/player/v2/config/' + LANG + '/%s'

# Rubriken der Mediathek, Kennung -> Menuename.
SECTIONS = (
    ('CIN', 'Filme'),
    ('SER', 'Serien'),
    ('HIS', 'Geschichte'),
    ('SCI', 'Wissenschaft'),
    ('CPO', 'Kultur und Pop'),
    ('DEC', 'Entdeckung der Welt'),
    ('ACT', 'Aktuelles und Gesellschaft'),
    ('AVN', 'Demnächst'),
)

IMAGE_SIZE = '940x530'
THUMB_SIZE = '380x214'


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    for code, title in SECTIONS:
        params.setParam('sUrl', URL_PAGE % code)
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
        # Arte schreibt bei Drosselung Klartext in die Antwort - das ist kein
        # Programmfehler, sondern eine Ratenbegrenzung.
        if 'Too Many Requests' in sContent:
            logger.info('-> [%s]: von der Gegenstelle gedrosselt (429)' % SITE_NAME)
        else:
            logger.info('-> [%s]: Antwort war kein gueltiges JSON: %s' % (SITE_NAME, sUrl))
        return {}


def _image(item, size):
    image = item.get('mainImage')
    if isinstance(image, dict) and image.get('url'):
        return image['url'].replace('__SIZE__', size)
    return ''


def _programId(sUrl):
    """Die Programmkennung steckt im Pfad: /videos/<id>/..."""
    if not sUrl:
        return ''
    isMatch, aResult = cParser.parseSingleResult(sUrl, r'/videos/([^/]+)/')
    return aResult if isMatch else ''


def showGenre():
    """Die Zonen einer Rubrik. Sie sind die eigentlichen Kategorien."""
    sUrl = ParameterHandler().getValue('sUrl')
    if not sUrl:
        cGui().showInfo()
        return
    jData = _getJson(sUrl, cacheTime=60 * 60 * 12)  # 12 Stunden
    params = ParameterHandler()
    total = 0
    for zone in jData.get('zones') or []:
        sTitle = zone.get('title')
        aData = ((zone.get('content') or {}).get('data')) or []
        if not sTitle or not aData:
            continue
        # Themen-Kacheln sind Verweise auf andere Seiten, keine Beitraege.
        if len([i for i in aData if (i.get('kind') or {}).get('code') != 'TOPIC']) < 2:
            continue
        params.setParam('sUrl', sUrl)
        params.setParam('sZone', zone.get('id') or sTitle)
        cGui().addFolder(cGuiElement(sTitle, SITE_IDENTIFIER, 'showEntries'), params)
        total += 1
    if not total:
        cGui().showInfo()
        return
    cGui().setEndOfDirectory()


def _collectItems(jData, sZone=''):
    """Sammelt die Beitraege - aus einer bestimmten Zone oder aus allen."""
    items = []
    for zone in jData.get('zones') or []:
        if sZone and (zone.get('id') or zone.get('title')) != sZone:
            continue
        for item in ((zone.get('content') or {}).get('data')) or []:
            if (item.get('kind') or {}).get('code') == 'TOPIC':
                continue  # Verweis auf eine andere Seite, kein Beitrag
            items.append(item)
    return items


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl:
        entryUrl = params.getValue('sUrl')
    cacheTime = 0
    if cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, False):
        cacheTime = 60 * 60 * 3  # 3 Stunden
    jData = _getJson(entryUrl, sGui, cacheTime)
    aItems = _collectItems(jData, '' if sSearchText else params.getValue('sZone'))

    if not aItems:
        if not sGui:
            oGui.showInfo()
        return

    total = len(aItems)
    for item in aItems:
        sName = item.get('title')
        sProgramId = item.get('programId') or _programId(item.get('url'))
        if not sName or not sProgramId:
            continue
        sSubtitle = item.get('subtitle')
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        # SHOW ist bei Arte eine Reihe, alles andere ein einzelner Beitrag.
        isShow = (item.get('kind') or {}).get('code') == 'SHOW'
        oGuiElement.setMediaType('tvshow' if isShow else 'movie')
        if sSubtitle:
            oGuiElement.setTitleSecond(sSubtitle)
        sDesc = item.get('shortDescription') or item.get('teaserText')
        if sDesc:
            oGuiElement.setDescription(sDesc)
        sThumb = _image(item, THUMB_SIZE)
        if sThumb:
            oGuiElement.setThumbnail(sThumb)
        sStart = ((item.get('availability') or {}).get('start')) or ''
        if len(sStart) >= 4 and sStart[:4].isdigit():
            oGuiElement.setYear(sStart[:4])
        params.setParam('entryUrl', URL_PLAYER % sProgramId)
        params.setParam('sName', sName)
        oGui.addFolder(oGuiElement, params, False, total)

    if not sGui:
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showHosters():
    """Die Streams eines Beitrags aus der Player-Konfiguration."""
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    if not sUrl:
        return hosters
    jData = _getJson(sUrl)
    attributes = ((jData.get('data') or {}).get('attributes')) or {}
    for stream in attributes.get('streams') or []:
        sLink = stream.get('url')
        if not sLink:
            continue
        sLabel = ((stream.get('mainQuality') or {}).get('label')) or ''
        # Aus "1080p" die reine Zahl ziehen, sonst bleibt die Qualitaet leer.
        sQuality = ''.join(c for c in sLabel if c.isdigit())
        sSlot = stream.get('slot') or ''
        sName = cParser.urlparse(sLink)
        sDisplayed = '%s [I]%s' % (sName, sSlot or 'Arte')
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
    # Arte liefert fertige HLS-Adressen, ResolveURL entfaellt.
    return [{'streamUrl': sUrl, 'resolved': True}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)
