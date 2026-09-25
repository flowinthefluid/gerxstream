# -*- coding: utf-8 -*-
# Python 3
"""Twitch-Live-Provider (delegierend, offiziell).

Wiedergabe/Konten ueber das offizielle Addon ``plugin.video.twitch``. Ohne
eigene Zugangsdaten oeffnet der Bereich einfach das Twitch-Addon. Optional:
mit eigener Client-ID (+ Secret) nutzt dieser Provider die Helix-API, um Live-
Streams zu finden (Sprach-/Spielfilter); Wiedergabe bleibt beim Twitch-Addon.
"""

import json

ADDON_ID = 'plugin.video.twitch'
_HELIX_STREAMS = 'https://api.twitch.tv/helix/streams'
_OAUTH_TOKEN = 'https://id.twitch.tv/oauth2/token'
_CACHE_TTL = 8 * 60


def is_addon_installed():
    try:
        import xbmc
        return xbmc.getCondVisibility('System.HasAddon(%s)' % ADDON_ID)
    except Exception:
        return False


def play_url(channel_login):
    """Wiedergabe-Deeplink des Twitch-Addons fuer einen Kanal."""
    return 'plugin://%s/?mode=play&channel_name=%s' % (ADDON_ID, channel_login)


def addon_root_url():
    return 'plugin://%s/' % ADDON_ID


def parse_streams(payload):
    """Helix streams-Antwort -> Liste einfacher Eintraege. Reine Funktion."""
    try:
        data = payload if isinstance(payload, dict) else json.loads(payload or '{}')
    except (TypeError, ValueError):
        return []
    entries = []
    for item in data.get('data', []) or []:
        login = item.get('user_login') or item.get('user_name')
        if not login:
            continue
        thumb = (item.get('thumbnail_url') or '').replace('{width}', '640').replace('{height}', '360')
        entries.append({
            'channel': login,
            'title': item.get('title') or login,
            'display': item.get('user_name') or login,
            'game': item.get('game_name') or '',
            'viewers': item.get('viewer_count') or 0,
            'language': item.get('language') or '',
            'thumb': thumb,
        })
    return entries


def _app_token(client_id, client_secret):
    """Client-Credentials-App-Token holen (nur mit Secret). Kurz gecacht."""
    if not client_id or not client_secret:
        return ''
    from urllib.parse import urlencode
    cache_key = 'twitch_token_%s' % client_id
    try:
        from resources.lib.tools import cCache
        cached = cCache().get(cache_key, 3600)
        if cached:
            return cached
        from resources.lib.handler.requestHandler import cRequestHandler
        data = urlencode({
            'client_id': client_id, 'client_secret': client_secret,
            'grant_type': 'client_credentials',
        })
        raw = cRequestHandler(_OAUTH_TOKEN, method='POST', data=data).request()
        token = (json.loads(raw) if raw else {}).get('access_token', '')
        if token:
            cCache().set(cache_key, token)
        return token
    except Exception:
        return ''


def get_streams(client_id, client_secret='', language='', first=25):
    """Live-Streams ueber Helix (nur mit Client-ID). fail-soft -> []."""
    if not client_id:
        return []
    token = _app_token(client_id, client_secret)
    if not token:
        return []
    from urllib.parse import urlencode
    params = {'first': first}
    if language:
        params['language'] = language
    url = '%s?%s' % (_HELIX_STREAMS, urlencode(params))
    cache_key = 'twitch_live_%s' % language
    try:
        from resources.lib.tools import cCache, logger
        cached = cCache().get(cache_key, _CACHE_TTL)
        if cached:
            return json.loads(cached)
        from resources.lib.handler.requestHandler import cRequestHandler
        handler = cRequestHandler(url)
        handler.addHeaderEntry('Client-Id', client_id)
        handler.addHeaderEntry('Authorization', 'Bearer %s' % token)
        raw = handler.request()
        entries = parse_streams(raw)
        cCache().set(cache_key, json.dumps(entries))
        return entries
    except Exception as exc:
        try:
            from resources.lib.tools import logger
            logger.error('-> [twitch]: Live-Abruf fehlgeschlagen: %s' % exc)
        except Exception:
            pass
        return []
