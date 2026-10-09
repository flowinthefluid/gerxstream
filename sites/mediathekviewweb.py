# -*- coding: utf-8 -*-
# Python 3
# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showEntries: 1 Stunde (Mediatheken aendern sich taeglich)
#
# MediathekViewWeb buendelt die oeffentlich-rechtlichen Mediatheken des
# deutschsprachigen Raums in einer einzigen, offenen Suchschnittstelle -
# ARD, ZDF, 3sat, arte, phoenix, ORF, SRF, die Dritten, KiKA, funk und
# weitere. Das Projekt ist quelloffen
# (github.com/mediathekview/mediathekviewweb).
#
# Damit deckt dieses eine Plugin ab, wofuer sonst ein Dutzend einzelner
# Mediathek-Scraper noetig waeren - und zwar durchweg legale Angebote.
#
# Aufbau, live geprueft:
#   POST /api/query mit JSON-Koerper
#     {"queries":[{"fields":["title"],"query":"<suchbegriff>"}],
#      "sortBy":"timestamp","sortOrder":"desc","future":false,
#      "offset":0,"size":50}
#   Antwort: result.results[] mit channel, topic, title, description,
#   duration, timestamp sowie url_video / url_video_hd / url_video_low
#   (direkte mp4-Adressen) und url_subtitle.
#   result.queryInfo.totalResults gibt die Gesamtzahl, bei der Aufnahme
#   717938 Eintraege insgesamt.

import json
import time

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'mediathekviewweb'
SITE_NAME = 'MediathekViewWeb'
SITE_ICON = 'mediathekviewweb.png'
CONTENT_CATEGORIES = ('filme', 'serien', 'dokus', 'kinder')

# Global search function is thus deactivated!
if not cConfig().getSettingBool('global_search_' + SITE_IDENTIFIER, True):
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'mediathekviewweb.de')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN
URL_QUERY = URL_MAIN + '/api/query'

PAGE_SIZE = 50

# Sender mit der Zahl der Eintraege zum Zeitpunkt der Aufnahme. Alle
# einzeln geprueft - Sender ohne Treffer waeren nur leere Menuepunkte.
CHANNELS = (
    ('ARD', 'ARD'),
    ('ONE', 'ONE'),
    ('tagesschau24', 'tagesschau24'),
    ('ARD-alpha', 'ARD-alpha'),
    ('ZDF', 'ZDF'),
    ('ZDFneo', 'ZDFneo'),
    ('ZDFinfo', 'ZDFinfo'),
    ('3sat', '3Sat'),
    ('arte', 'ARTE.DE'),
    ('phoenix', 'PHOENIX'),
    ('BR', 'BR'),
    ('HR', 'HR'),
    ('MDR', 'MDR'),
    ('NDR', 'NDR'),
    ('RBB', 'RBB'),
    ('Radio Bremen', 'Radio Bremen TV'),
    ('SR', 'SR'),
    ('SWR', 'SWR'),
    ('WDR', 'WDR'),
    ('KiKA', 'KiKA'),
    ('ZDFtivi', 'ZDF-tivi'),
    ('funk', 'funk'),
    ('Deutsche Welle', 'DW'),
    ('ORF', 'ORF'),
    ('SRF', 'SRF'),
)

# Themenbereiche als vorkonfigurierte Suchen ueber alle Sender hinweg.
TOPICS = (
    ('Dokumentationen', 'doku'),
    ('Reportagen', 'reportage'),
    ('Wissenschaft', 'wissen'),
    ('Geschichte', 'geschichte'),
    ('Natur und Tiere', 'natur'),
    ('Politik', 'politik'),
    ('Kultur', 'kultur'),
    ('Film', 'spielfilm'),
    ('Krimi', 'krimi'),
    ('Kinder', 'kinder'),
    ('Comedy und Satire', 'comedy'),
    ('Sport', 'sport'),
)


def load():  # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('mvwMode', 'latest')
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30500), SITE_IDENTIFIER, 'showEntries'), params)  # Neues
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30839), SITE_IDENTIFIER, 'showGenres'), params)  # Sender
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30507), SITE_IDENTIFIER, 'showGenre'), params)  # Kategorien
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'))  # Suche
    cGui().setEndOfDirectory()


def showGenres():
    """Senderliste."""
    params = ParameterHandler()
    for sLabel, sChannel in CHANNELS:
        params.setParam('mvwMode', 'channel')
        params.setParam('mvwValue', sChannel)
        params.setParam('mvwChannel', sChannel)
        params.setParam('page', '0')
        cGui().addFolder(cGuiElement(sLabel, SITE_IDENTIFIER, 'showChannel'), params)
    cGui().setEndOfDirectory()


def showChannel():
    params = ParameterHandler()
    channel = params.getValue('mvwChannel') or params.getValue('mvwValue')
    if channel not in dict(CHANNELS).values():
        cGui().showInfo()
        return
    params.setParam('mvwChannel', channel)
    params.setParam('mvwMode', 'channel')
    params.setParam('mvwValue', channel)
    params.setParam('page', '0')
    for title, function in (
            (cConfig().getLocalizedString(30500), 'showEntries'),
            (cConfig().getLocalizedString(31505) or 'Themenfilter', 'showGenre'),
            (cConfig().getLocalizedString(30520), 'showSearch')):
        cGui().addFolder(cGuiElement(title, SITE_IDENTIFIER, function), params)
    cGui().setEndOfDirectory()


def showGenre():
    """Themenbereiche als Suche ueber alle Sender."""
    params = ParameterHandler()
    for sLabel, sQuery in TOPICS:
        params.setParam('mvwMode', 'topic')
        params.setParam('mvwValue', sQuery)
        params.setParam('page', '0')
        cGui().addFolder(cGuiElement(sLabel, SITE_IDENTIFIER, 'showEntries'), params)
    cGui().setEndOfDirectory()


def _query(mode, value, page, sGui=False, channel=''):
    """Stellt die Abfrage an die API. Liefert (Treffer, Gesamtzahl)."""
    if mode == 'channel':
        queries = [{'fields': ['channel'], 'query': value}]
    elif mode == 'topic':
        queries = [{'fields': ['topic', 'title'], 'query': value}]
    elif mode == 'search':
        queries = [{'fields': ['title', 'topic'], 'query': value}]
    else:  # latest
        queries = []

    if channel and mode != 'channel':
        queries.insert(0, {'fields': ['channel'], 'query': channel})

    payload = json.dumps({
        'queries': queries,
        'sortBy': 'timestamp',
        'sortOrder': 'desc',
        'future': False,
        'offset': page * PAGE_SIZE,
        'size': PAGE_SIZE,
    })

    oRequest = cRequestHandler(URL_QUERY, caching=False,
                               ignoreErrors=(sGui is not False),
                               method='POST', data=payload)
    # Die API erwartet den JSON-Koerper als text/plain; mit
    # application/json antwortet sie mit einem Fehler.
    oRequest.addHeaderEntry('Content-Type', 'text/plain')
    sContent = oRequest.request()
    if not sContent:
        logger.info('-> [%s]: keine Antwort von der API' % SITE_NAME)
        return [], 0
    try:
        jData = json.loads(sContent)
    except ValueError:
        logger.info('-> [%s]: Antwort war kein gueltiges JSON' % SITE_NAME)
        return [], 0
    if jData.get('err'):
        logger.info('-> [%s]: API meldet Fehler: %s' % (SITE_NAME, str(jData['err'])[:160]))
        return [], 0
    result = jData.get('result') or {}
    total = ((result.get('queryInfo') or {}).get('totalResults')) or 0
    return (result.get('results') or []), total


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()

    if sSearchText:
        mode, value = 'search', sSearchText
        page = 0
    else:
        mode = params.getValue('mvwMode') or 'latest'
        value = params.getValue('mvwValue') or ''
        sPage = params.getValue('page')
        page = int(sPage) if isinstance(sPage, str) and sPage.isdigit() else 0

    channel = '' if sGui else (params.getValue('mvwChannel') or '')
    params.setParam('mvwChannel', channel)
    aResults, total = _query(mode, value, page, sGui, channel=channel)
    if not aResults:
        if not sGui:
            oGui.showInfo()
        return

    for item in aResults:
        sTitle = item.get('title')
        # Die drei Qualitaetsstufen sind einzelne Felder; die beste zuerst.
        sVideo = (item.get('url_video_hd') or item.get('url_video')
                  or item.get('url_video_low'))
        if not sTitle or not sVideo:
            continue

        sChannel = item.get('channel') or ''
        sTopic = item.get('topic') or ''
        # Sender und Sendereihe voranstellen, sonst sind gleichnamige
        # Folgen verschiedener Sender nicht unterscheidbar.
        sLabel = sTitle
        if sTopic and sTopic != sTitle:
            sLabel = '%s - %s' % (sTopic, sTitle)
        if sChannel:
            sLabel = '[%s] %s' % (sChannel, sLabel)

        oGuiElement = cGuiElement(sLabel, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setMediaType('movie')
        if item.get('description'):
            oGuiElement.setDescription(item['description'])
        iTimestamp = item.get('timestamp')
        if isinstance(iTimestamp, int) and iTimestamp > 0:
            try:
                oGuiElement.setYear(time.strftime('%Y', time.gmtime(iTimestamp)))
            except (ValueError, OSError):
                pass

        params.setParam('mvwVideo', sVideo)
        params.setParam('sName', sLabel)
        oGui.addFolder(oGuiElement, params, False, len(aResults))

    if not sGui:
        # Weiterblaettern, solange die API mehr meldet als bisher geholt.
        if (page + 1) * PAGE_SIZE < total:
            params.setParam('mvwMode', mode)
            params.setParam('mvwValue', value)
            params.setParam('page', str(page + 1))
            oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showHosters():
    """Die Adresse steht bereits in der Liste - kein weiterer Abruf noetig."""
    sVideo = ParameterHandler().getValue('mvwVideo')
    if not sVideo:
        return []
    hosters = [{'link': sVideo, 'name': SITE_NAME,
                'displayedName': '%s [I]Mediathek[/I]' % SITE_NAME},
               'getHosterUrl']
    return hosters


def getHosterUrl(sUrl=False):
    # Direkte mp4-Adressen der Mediatheken, kein Resolver noetig.
    return [{'streamUrl': sUrl, 'resolved': True}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText:
        return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(False, oGui, sSearchText)
