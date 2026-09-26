# -*- coding: utf-8 -*-
# Python 3
"""Pluto TV: kostenlose, werbefinanzierte Sender (offizielle Schnittstelle).

Pluto TV braucht kein Konto. Die Webseite holt sich beim Start anonym eine
Sitzung (``boot.pluto.tv``) und bekommt damit Senderliste und Stream-
Adressen fuer das Land, aus dem sie aufgerufen wird. Genau das macht auch
dieser Provider - ohne fremde Partner-Schluessel.

Die Sitzung laeuft ab. Im Katalog steht deshalb eine Stream-Adresse ohne
Sitzung; ``resolve_url`` haengt beim Abspielen eine frische an. Die
Senderliste wird im Profil zwischengespeichert und vom Dienst beim Kodi-Start
erneuert (``refresh``), damit der Menueaufbau nicht ins Netz muss.
"""

import json
import os
import re
import time
import uuid
from urllib.parse import quote

from resources.lib.config import cConfig
from resources.lib.livestreams.providers.base import Provider
from resources.lib.tools import logger

PROVIDER_ID = 'pluto'
BOOT_URL = ('https://boot.pluto.tv/v4/start?appName=web&appVersion=9.10.0&deviceVersion=140.0.0'
            '&deviceModel=web&deviceMake=chrome&deviceType=web&clientID=%s'
            '&clientModelNumber=1.0.0&serverSideAds=false&drmCapabilities=')
CHANNELS_URL = ('https://service-channels.clusters.pluto.tv/v2/guide/channels'
                '?channelIds=&offset=0&limit=1000&sort=number%3Aasc')
CATEGORIES_URL = 'https://service-channels.clusters.pluto.tv/v2/guide/categories'
STITCH_PATH = '/v2/stitch/hls/channel/%s/master.m3u8'
DEFAULT_STITCHER = 'https://cfd-v4-service-channel-stitcher-use1-1.prd.pluto.tv'
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/140.0 Safari/537.36')

CHANNELS_FILE = 'pluto_channels.json'
SESSION_FILE = 'pluto_session.json'
CHANNELS_MAX_AGE = 24 * 60 * 60
SESSION_MAX_AGE = 4 * 60 * 60

# Pluto-Kategorie (Kleinbuchstaben, Teilstring) -> Genre im Katalog
CATEGORY_GENRES = (
    ('sport', 'sports'), ('crime', 'series'), ('krimi', 'series'), ('sitcom', 'comedy'),
    ('comedy', 'comedy'), ('film', 'movies'), ('movie', 'movies'), ('serie', 'series'),
    ('sci-fi', 'series'), ('doku', 'doc'), ('wissen', 'doc'), ('true crime', 'doc'),
    ('anime', 'anime'), ('western', 'movies'), ('action', 'movies'), ('reality', 'series'),
    ('kids', 'kids'), ('kinder', 'kids'), ('nachrichten', 'news'), ('news', 'news'),
    ('musik', 'music'), ('music', 'music'), ('south park', 'comedy'), ('star trek', 'series'),
)
ADULT_CATEGORIES = re.compile(r'sinnlich|erotik|romantik pur|sensual', re.I)
# Motorsport-/Racing-Sender auch ausserhalb der Sportkategorien.
RACING_NAMES = re.compile(r'red bull|motor|racing|rally|top gear|speed|motorsport|drift|gp\b', re.I)
# Auf Wunsch nicht im Katalog.
EXCLUDED_NAMES = re.compile(r'\bnfl\b|american football|baseball|\bmlb\b|college football', re.I)


def _profile_path(name):
    from xbmcvfs import translatePath
    directory = os.path.join(translatePath(cConfig().getAddonInfo('profile')), 'livestreams')
    if not os.path.isdir(directory):
        os.makedirs(directory)
    return os.path.join(directory, name)


def _load(name):
    try:
        with open(_profile_path(name), 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (IOError, OSError, ValueError, TypeError):
        return {}


def _save(name, data):
    path = _profile_path(name)
    temporary = path + '.new'
    try:
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(',', ':'))
        os.replace(temporary, path)
    except (IOError, OSError, TypeError, ValueError) as exc:
        logger.error('-> [providers.pluto]: %s nicht schreibbar: %s' % (name, exc))


def _get_json(url, token=''):
    from resources.lib.handler.requestHandler import cRequestHandler
    handler = cRequestHandler(url, caching=False, ignoreErrors=True, allow_insecure_tls=False)
    handler.addHeaderEntry('User-Agent', USER_AGENT)
    if token:
        handler.addHeaderEntry('Authorization', 'Bearer %s' % token)
    try:
        data = json.loads(handler.request() or '{}')
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, (dict, list)) else {}


def session(force=False):
    """Gueltige anonyme Sitzung: {'token', 'params', 'stitcher', 'region', 'ts'}."""
    stored = _load(SESSION_FILE)
    age = time.time() - float(stored.get('ts') or 0)
    if not force and stored.get('token') and age < min(SESSION_MAX_AGE, float(stored.get('ttl') or SESSION_MAX_AGE)):
        return stored
    boot = _get_json(BOOT_URL % uuid.uuid4())
    if not isinstance(boot, dict) or not boot.get('sessionToken'):
        logger.error('-> [providers.pluto]: keine Sitzung erhalten')
        return stored if stored.get('token') else {}
    fresh = {
        'token': boot['sessionToken'],
        'params': boot.get('stitcherParams') or '',
        'stitcher': (boot.get('servers') or {}).get('stitcher') or DEFAULT_STITCHER,
        'region': str((boot.get('session') or {}).get('activeRegion') or 'de').lower(),
        'ttl': max(600, int(boot.get('refreshInSec') or SESSION_MAX_AGE) - 300),
        'ts': time.time(),
    }
    _save(SESSION_FILE, fresh)
    return fresh


def resolve_url(channel_id):
    """Abspielbare Stream-Adresse mit frischer Sitzung, sonst ''."""
    if not re.fullmatch(r'[a-f0-9]{24}', str(channel_id or '')):
        return ''
    current = session()
    if not current.get('token'):
        return ''
    url = current['stitcher'].rstrip('/') + STITCH_PATH % channel_id
    return '%s?%s&jwt=%s&masterJWTPassthrough=true' % (url, current['params'], quote(current['token'], safe=''))


def channel_id_from_url(url):
    match = re.search(r'/stitch/hls/channel/([a-f0-9]{24})/', url or '')
    return match.group(1) if match else ''


def _logo(images):
    for wanted in ('colorLogoPNG', 'solidLogoPNG', 'logo'):
        for image in images or ():
            if isinstance(image, dict) and image.get('type') == wanted and image.get('url'):
                return image['url']
    return ''


def build_channels(raw_channels, categories, region):
    """Rohdaten der Schnittstelle -> Katalog-Kanaele (reine Funktion, testbar)."""
    category_of = {}
    for category in categories or ():
        if not isinstance(category, dict):
            continue
        for cid in category.get('channelIDs') or ():
            category_of.setdefault(cid, []).append(str(category.get('name') or ''))
    country = region if re.fullmatch(r'[a-z]{2}', region or '') else 'de'
    result = []
    for raw in raw_channels or ():
        if not isinstance(raw, dict) or not re.fullmatch(r'[a-f0-9]{24}', str(raw.get('id') or '')):
            continue
        name = str(raw.get('name') or '').strip()
        if not name or EXCLUDED_NAMES.search(name) or raw.get('plutoOfficeOnly'):
            continue
        names = category_of.get(raw['id'], [])
        if any(EXCLUDED_NAMES.search(c) for c in names):
            continue
        genres = set()
        for category in names:
            lowered = category.lower()
            for key, genre in CATEGORY_GENRES:
                if key in lowered:
                    genres.add(genre)
        adult = any(ADULT_CATEGORIES.search(c) for c in names)
        if adult:
            genres.add('adult')
        sports = 'sports' in genres or bool(RACING_NAMES.search(name))
        if sports:
            genres.add('sports')
        result.append({
            'id': 'gxs:%s:%s:pluto-%s' % ('sports' if sports else 'tv', country, raw['id']),
            'name': name,
            'section': 'sports' if sports else 'tv',
            'country': country,
            'language': ['de'] if country in ('de', 'at', 'ch') else [],
            'genre': sorted(genres) or ['series'],
            'nsfw': adult,
            'publisher': 'pluto-tv',
            'logo': _logo(raw.get('images')),
            'epg_id': '',
            'sources': [{
                'source_id': 'pluto-%s' % raw['id'],
                'provider_id': PROVIDER_ID,
                'display_name': 'Pluto TV',
                'url': DEFAULT_STITCHER + STITCH_PATH % raw['id'],
                'protocol': 'hls',
                'quality': 'hd',
                'official': True,
                'reliability': 'medium',
                'region': country,
                'resolver': PROVIDER_ID,
                'active': True,
            }],
        })
    return result


def refresh(force=False):
    """Senderliste neu laden (Dienst). Liefert die Zahl der Sender oder -1."""
    stored = _load(CHANNELS_FILE)
    if not force and time.time() - float(stored.get('ts') or 0) < CHANNELS_MAX_AGE and stored.get('channels'):
        return len(stored['channels'])
    built = []
    for _attempt in range(2):  # ein zweiter Versuch bei kurzen Aussetzern
        current = session(force=True)
        if not current.get('token'):
            continue
        channels = _get_json(CHANNELS_URL, current['token'])
        categories = _get_json(CATEGORIES_URL, current['token'])
        raw = channels.get('data') if isinstance(channels, dict) else channels
        cats = categories.get('data') if isinstance(categories, dict) else categories
        built = build_channels(raw, cats, current.get('region', 'de'))
        if built:
            break
    if not built:
        logger.error('-> [providers.pluto]: keine Sender erhalten')
        return -1
    _save(CHANNELS_FILE, {'ts': time.time(), 'region': current.get('region'), 'channels': built})
    logger.info('-> [providers.pluto]: %d Sender geladen (%s)' % (len(built), current.get('region')))
    return len(built)


class PlutoProvider(Provider):
    id = PROVIDER_ID

    def channels(self):
        if not cConfig().getSettingBool('lsPlutoEnabled', True):
            return []
        stored = _load(CHANNELS_FILE)
        if not stored.get('channels'):
            # Erster Start vor dem ersten Dienstlauf: einmalig selbst laden.
            refresh(force=True)
            stored = _load(CHANNELS_FILE)
        return list(stored.get('channels') or [])

    def signature(self):
        stored = _load(CHANNELS_FILE)
        return 'pluto|%s|%s' % (cConfig().getSettingBool('lsPlutoEnabled', True), int(stored.get('ts') or 0))
