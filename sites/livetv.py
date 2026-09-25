# -*- coding: utf-8 -*-
# Python 3
"""Direkte HLS-Livestreams oeffentlich-rechtlicher Fernsehsender.

Das ist ein kuratiertes Medienverzeichnis, kein PVR-Client: Es gibt bewusst
weder EPG noch Senderlisten-Import oder DRM-Umgehung. Jeder Eintrag zeigt
auf den vom Sender bereitgestellten HLS-Livestream.
"""

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.gui.gui import cGui
from resources.lib.config import cConfig
from resources.lib.tools import logger


SITE_IDENTIFIER = 'livetv'
SITE_NAME = 'Oeffentlich-rechtliches Live-TV'
CONTENT_CATEGORIES = ('live',)
SITE_GLOBAL_SEARCH = False
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)


# Direkte HLS-Feeds ohne Konto, DRM oder technische Zugriffsumgehung.
# Playlist und ein aktuelles Segment wurden am 2026-09-25 abgerufen. Die
# Sender koennen ihre Ausspielung ausserhalb Deutschlands einschraenken.
CHANNELS = (
    {
        'title': 'Das Erste',
        'description': 'Das Erste - 24/7-Livestream der ARD.',
        'stream': 'https://daserste-live.ard-mcdn.de/daserste/live/hls/de/master.m3u8',
    },
    {
        'title': 'ZDF',
        'description': 'ZDF - 24/7-Livestream.',
        'stream': 'https://zdf-hls-15.akamaized.net/hls/live/2016498/de/high/master.m3u8',
    },
    {
        'title': 'Arte',
        'description': 'Arte Deutsch - 24/7-Livestream.',
        'stream': 'https://artesimulcast.akamaized.net/hls/live/2030993/artelive_de/index.m3u8',
    },
    {
        'title': 'WDR Fernsehen',
        'description': 'WDR Fernsehen - 24/7-Livestream.',
        'stream': 'https://wdr-live.ard-mcdn.de/wdr/live/hls/de/master.m3u8',
    },
    {
        'title': 'rbb Fernsehen Berlin',
        'description': 'rbb Fernsehen Berlin - 24/7-Livestream.',
        'stream': 'https://rbb-hls-berlin.akamaized.net/hls/live/2017824/rbb_berlin/master.m3u8',
    },
    {
        'title': 'KiKA',
        'description': 'KiKA - 24/7-Livestream.',
        'stream': 'https://kika-live.ard-mcdn.de/kika/live/hls/de/master.m3u8',
    },
    {
        'title': 'hr Fernsehen',
        'description': 'hr Fernsehen - 24/7-Livestream.',
        'stream': 'https://hr-live.ard-mcdn.de/hr/live/hls/de/master.m3u8',
    },
)


def load():
    """Listet die Sender direkt als abspielbare Eintraege."""
    logger.info('Load %s' % SITE_NAME)
    oGui = cGui()
    total = len(CHANNELS)
    for channel in CHANNELS:
        params = ParameterHandler()
        params.setParam('streamUrl', channel['stream'])
        oGuiElement = cGuiElement(channel['title'], SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setDescription(channel['description'])
        oGuiElement.setInfo('LIVE')
        oGui.addFolder(oGuiElement, params, False, total)
    oGui.setEndOfDirectory()


def showHosters():
    """Uebergibt genau einen finalen HLS-Feed an den Standard-Player."""
    sUrl = ParameterHandler().getValue('streamUrl')
    if not sUrl:
        return []
    return [
        {'link': sUrl, 'name': 'HLS', 'displayedName': 'HLS-Livestream'},
        'getHosterUrl',
    ]


def getHosterUrl(sUrl=False):
    """HLS ist eine finale Medienadresse und braucht ResolveURL nicht."""
    if not sUrl:
        return []
    return [{'streamUrl': sUrl, 'resolved': True}]
