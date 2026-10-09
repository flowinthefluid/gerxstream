# -*- coding: utf-8 -*-
import re

import requests
import xbmc
import xbmcgui

from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler

SITE_IDENTIFIER = 'rocketbeans'
SITE_NAME = 'Rocket Beans TV'
SITE_ICON = 'dokus4me.png'
CONTENT_CATEGORIES = ('serien', 'dokus')
SITE_GLOBAL_SEARCH = False
DOMAIN = 'rocketbeans.tv'
URL_MAIN = 'https://rocketbeans.tv'
API_MAIN = 'https://api.rocketbeans.tv'
PAGE_SIZE = 50
TOKEN_SETTING = 'rocketbeans.token'


def _text(identifier, fallback):
    return cConfig().getLocalizedString(identifier) or fallback


def _call(path, method='GET', payload=None, authenticated=True):
    if not path.startswith('/v1/'):
        return {}
    headers = {'Accept': 'application/json'}
    token = cConfig().getSetting(TOKEN_SETTING, '') if authenticated else ''
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        response = requests.request(method, API_MAIN + path, headers=headers,
                                    json=payload, timeout=20, allow_redirects=False)
        if response.status_code == 401 and token:
            cConfig().setSetting(TOKEN_SETTING, '')
        if response.status_code != 200:
            return {}
        result = response.json()
        return result if isinstance(result, dict) and result.get('success') is True else {}
    except (requests.RequestException, ValueError):
        return {}


def _thumbnail(item):
    images = item.get('thumbnail') or []
    for name in ('large', 'medium', 'small'):
        for image in images:
            if image.get('name') == name and image.get('url'):
                return image['url']
    return ''


def _offset(params):
    value = params.getValue('offset')
    return int(value) if isinstance(value, str) and value.isdigit() else 0


def load():
    params = ParameterHandler()
    params.setParam('offset', '0')
    params.setParam('rbMode', 'latest')
    cGui().addFolder(cGuiElement(_text(30500, 'Neu'), SITE_IDENTIFIER, 'showEpisodes'), params)
    cGui().addFolder(cGuiElement(_text(31507, 'Sendungen A-Z'), SITE_IDENTIFIER, 'showShows'), params)
    if cConfig().getSetting(TOKEN_SETTING, ''):
        params.setParam('rbMode', 'subscriptions')
        cGui().addFolder(cGuiElement(_text(31514, 'Meine Abos'), SITE_IDENTIFIER, 'showEpisodes'), params)
    cGui().setEndOfDirectory()


def showShows():
    params = ParameterHandler()
    offset = _offset(params)
    result = _call('/v1/media/show/preview/all?offset=%d&limit=%d&sortby=Title&order=ASC' %
                   (offset, PAGE_SIZE))
    items = result.get('data') or []
    if not items:
        cGui().showInfo()
        return
    for item in items:
        if not item.get('id') or not item.get('title') or item.get('isTruePodcast'):
            continue
        element = cGuiElement(item['title'], SITE_IDENTIFIER, 'showSeasons')
        element.setThumbnail(_thumbnail(item))
        element.setMediaType('tvshow')
        params.setParam('showId', item['id'])
        params.setParam('offset', '0')
        cGui().addFolder(element, params)
    _nextPage(result, offset, 'showShows', params)
    cGui().setEndOfDirectory()


def showSeasons():
    params = ParameterHandler()
    showId = params.getValue('showId')
    if not isinstance(showId, str) or not showId.isdigit():
        return
    result = _call('/v1/media/show/' + showId)
    data = result.get('data') or {}
    if not data:
        cGui().showInfo()
        return
    params.setParam('rbMode', 'show')
    params.setParam('offset', '0')
    cGui().addFolder(cGuiElement(_text(31508, 'Alle Folgen'), SITE_IDENTIFIER, 'showEpisodes'), params)
    for season in data.get('seasons') or []:
        title = season.get('name') or season.get('title')
        if not season.get('id') or not title:
            continue
        params.setParam('rbMode', 'season')
        params.setParam('seasonId', season['id'])
        element = cGuiElement(title, SITE_IDENTIFIER, 'showEpisodes')
        element.setThumbnail(_thumbnail(season))
        cGui().addFolder(element, params)
    cGui().setEndOfDirectory()


def _nextPage(result, offset, function, params):
    total = (result.get('pagination') or {}).get('total') or 0
    if offset + PAGE_SIZE < total:
        params.setParam('offset', str(offset + PAGE_SIZE))
        cGui().addNextPage(SITE_IDENTIFIER, function, params)


def showEpisodes():
    params = ParameterHandler()
    offset = _offset(params)
    mode = params.getValue('rbMode') or 'latest'
    if mode in ('show', 'season'):
        identifier = params.getValue('showId' if mode == 'show' else 'seasonId')
        if not isinstance(identifier, str) or not identifier.isdigit():
            return
        path = '/v1/media/episode/by%s/preview/%s' % (mode, identifier)
    elif mode == 'subscriptions':
        if not cConfig().getSetting(TOKEN_SETTING, ''):
            cGui().showInfo(SITE_NAME, _text(31512, 'Bitte unter Konten anmelden.'))
            return
        path = '/v1/media/abobox/self'
    else:
        path = '/v1/media/episode/preview/newest'
    result = _call(path + '?offset=%d&limit=%d&order=DESC' % (offset, PAGE_SIZE))
    items = result.get('data') or []
    if not items:
        cGui().showInfo()
        return
    for item in items:
        if not item.get('id') or not item.get('title'):
            continue
        element = cGuiElement(item['title'], SITE_IDENTIFIER, 'showHosters')
        element.setThumbnail(_thumbnail(item))
        element.setDescription(item.get('description') or '')
        element.setMediaType('episode')
        params.setParam('episodeId', item['id'])
        params.setParam('sName', item['title'])
        cGui().addFolder(element, params, False, len(items))
    _nextPage(result, offset, 'showEpisodes', params)
    cGui().setView('episodes')
    cGui().setEndOfDirectory()


def _youtubeId(result, episodeId):
    data = result.get('data') or {}
    for episode in data.get('episodes') or []:
        if str(episode.get('id')) != str(episodeId) or episode.get('isAvailable') is False:
            continue
        if episode.get('rbscExclusive'):
            return ''
        for token in episode.get('tokens') or []:
            identifier = token.get('token') or ''
            if token.get('type') == 'youtube' and re.fullmatch(r'[A-Za-z0-9_-]{11}', identifier):
                return identifier
    return ''


def showHosters():
    episodeId = ParameterHandler().getValue('episodeId')
    if not isinstance(episodeId, str) or not episodeId.isdigit():
        return []
    identifier = _youtubeId(_call('/v1/media/episode/' + episodeId), episodeId)
    if not identifier:
        cGui().showInfo(SITE_NAME, _text(31513, 'Kein freier YouTube-Stream vorhanden. Supporter-Player noch nicht unterstuetzt.'))
        return []
    if not xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube)'):
        xbmc.executebuiltin('InstallAddon(plugin.video.youtube)')
        return []
    link = 'plugin://plugin.video.youtube/play/?video_id=' + identifier
    return [{'link': link, 'name': 'YouTube', 'displayedName': 'YouTube'}, 'getHosterUrl']


def getHosterUrl(sUrl=False):
    if not isinstance(sUrl, str) or not re.fullmatch(
            r'plugin://plugin\.video\.youtube/play/\?video_id=[A-Za-z0-9_-]{11}', sUrl):
        return []
    return [{'streamUrl': sUrl, 'resolved': True}]


def login():
    config = cConfig()
    config.setSetting(TOKEN_SETTING, '')
    email = config.getSetting('rocketbeans.user', '')
    password = config.getSetting('rocketbeans.pass', '')
    if not email or not password:
        cGui().showInfo(SITE_NAME, _text(31512, 'Bitte unter Konten anmelden.'))
        return False
    code = xbmcgui.Dialog().input(_text(31515, '2FA-Code (optional)'))
    payload = {'email': email, 'password': password}
    if code:
        payload['secondFactorToken'] = code
    result = _call('/v1/auth/local', method='POST', payload=payload, authenticated=False)
    token = (result.get('data') or {}).get('token')
    if not isinstance(token, str) or not token or '\r' in token or '\n' in token:
        cGui().showInfo(SITE_NAME, _text(31516, 'Anmeldung fehlgeschlagen. Zugangsdaten/2FA pruefen; eventuell ist eine Browser-Captcha-Anmeldung erforderlich.'))
        return False
    config.setSetting(TOKEN_SETTING, token)
    config.setSetting('rocketbeans.pass', '')
    cGui().showInfo(SITE_NAME, _text(31517, 'Angemeldet.'))
    return True


def logout():
    _call('/v1/auth/logout', method='POST')
    cConfig().setSetting(TOKEN_SETTING, '')
    cConfig().setSetting('rocketbeans.pass', '')
    cGui().showInfo(SITE_NAME, _text(31518, 'Abgemeldet.'))