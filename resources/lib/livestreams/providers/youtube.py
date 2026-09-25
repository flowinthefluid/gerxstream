# -*- coding: utf-8 -*-
# Python 3
"""YouTube-Live-Provider (delegierend, offiziell).

Wiedergabe und Kontoverwaltung laufen ueber das offizielle Addon
``plugin.video.youtube`` - kein Scraping, kein yt-dlp-Shellout im Addon. Ohne
eigenen Schluessel oeffnet der Bereich einfach das YouTube-Addon (dort ist
Anonym-Browsing, Login und Playlist-Zuordnung bereits geloest).

Optional: hinterlegt der Nutzer einen eigenen YouTube-Data-API-v3-Key, bietet
dieser Provider zusaetzlich eine Live-Suche mit Kategorie-/Laenderfilter; die
gefundenen Videos spielt weiterhin das YouTube-Addon.
"""

import json

ADDON_ID = 'plugin.video.youtube'
_API_SEARCH = 'https://www.googleapis.com/youtube/v3/search'
_CACHE_TTL = 8 * 60  # 8 Minuten (Rate-Limits schonen)

# YouTube-Videokategorie-IDs (stabil).
CATEGORIES = (
    ('gaming', '20', 31300, 'Gaming'),
    ('music',  '10', 31301, 'Musik'),
    ('news',   '25', 31302, 'Nachrichten'),
    ('sports', '17', 31303, 'Sport'),
)


def is_addon_installed():
    try:
        import xbmc
        return xbmc.getCondVisibility('System.HasAddon(%s)' % ADDON_ID)
    except Exception:
        return False


def play_url(video_id):
    """Stabiler Wiedergabe-Deeplink des YouTube-Addons."""
    return 'plugin://%s/play/?video_id=%s' % (ADDON_ID, video_id)


def addon_root_url():
    return 'plugin://%s/' % ADDON_ID


def parse_search_results(payload):
    """search.list-Antwort -> Liste einfacher Eintraege. Reine Funktion."""
    try:
        data = payload if isinstance(payload, dict) else json.loads(payload or '{}')
    except (TypeError, ValueError):
        return []
    entries = []
    for item in data.get('items', []) or []:
        vid = (item.get('id') or {}).get('videoId')
        snippet = item.get('snippet') or {}
        if not vid:
            continue
        entries.append({
            'video_id': vid,
            'title': snippet.get('title') or vid,
            'channel': snippet.get('channelTitle') or '',
            'thumb': (((snippet.get('thumbnails') or {}).get('medium') or {}).get('url')) or '',
        })
    return entries


def search_live(api_key, category_id='', region_code='', query='', max_results=25):
    """Live-Videos ueber die offizielle API suchen (nur mit Nutzer-Key).

    Gibt [] zurueck bei fehlendem Key/Fehler (fail-soft). Ergebnis wird kurz
    gecacht, um API-Limits zu respektieren.
    """
    if not api_key:
        return []
    from urllib.parse import urlencode
    params = {
        'part': 'snippet', 'eventType': 'live', 'type': 'video',
        'maxResults': max_results, 'key': api_key,
    }
    if category_id:
        params['videoCategoryId'] = category_id
    if region_code:
        params['regionCode'] = region_code
    params['q'] = query or 'live'
    url = '%s?%s' % (_API_SEARCH, urlencode(params))

    cache_key = 'yt_live_%s_%s_%s' % (category_id, region_code, query)
    try:
        from resources.lib.tools import cCache, logger
        cached = cCache().get(cache_key, _CACHE_TTL)
        if cached:
            return json.loads(cached)
        from resources.lib.handler.requestHandler import cRequestHandler
        raw = cRequestHandler(url).request()
        entries = parse_search_results(raw)
        cCache().set(cache_key, json.dumps(entries))
        return entries
    except Exception as exc:
        try:
            from resources.lib.tools import logger
            logger.error('-> [youtube]: Live-Suche fehlgeschlagen: %s' % exc)
        except Exception:
            pass
        return []
