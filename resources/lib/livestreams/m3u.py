# -*- coding: utf-8 -*-
# Python 3
"""M3U-Playlist-Generator fuer den IPTV Simple Client.

Erzeugt aus dem sichtbaren Katalog eine M3U-Playlist. Jeder Kanal wird nach
Land UND Genre gruppiert (mehrere Gruppen via ';' im group-title, wie vom
IPTV Simple Client unterstuetzt). Es wird pro Kanal genau EINE Stream-Zeile
geschrieben - und zwar ein ``plugin://``-Aufruf zurueck ins Addon, damit
Quellenwahl, HD/SD-Fallback und automatischer Quellenwechsel an einer Stelle
bleiben und der Export rotierende Upstream-URLs ueberlebt.

Alles laeuft durch ``contentgate`` (fail-closed). Bei NSFW=aus enthaelt die
M3U keinen einzigen NSFW-Kanal und keine Erotik-Gruppe.
"""

from urllib.parse import urlencode

from resources.lib import contentgate
from resources.lib.livestreams import catalog, selector, taxonomy

ADDON_ID = 'plugin.video.gerxstream'


def _plugin_play_url(channel):
    """plugin://-URL, die im Addon die Quellenwahl/Failover ausloest."""
    query = urlencode({
        'site': 'livestreams',
        'function': 'play',
        'channel': channel['id'],
        'playMode': 'play',
    })
    return 'plugin://%s/?%s' % (ADDON_ID, query)


def _direct_url(channel):
    """Roh-URL der besten Quelle (optionaler Direktmodus ohne Addon-Umweg)."""
    source = selector.best_source(channel)
    if not source:
        return None
    url = source['url']
    if source.get('headers'):
        # IPTV Simple / inputstream.adaptive erwarten Header als '|'-Suffix.
        header = '&'.join('%s=%s' % (k, v) for k, v in source['headers'].items())
        url = '%s|%s' % (url, header)
    return url


def _groups(channel):
    groups = [taxonomy.section_label(channel['section'])]
    country = channel.get('country')
    if country:
        groups.append(taxonomy.country_label(country))
    for genre in channel.get('genre') or []:
        if genre == contentgate.NSFW_GENRE and not contentgate.is_nsfw_enabled():
            continue
        if contentgate.is_genre_visible(genre):
            groups.append(taxonomy.genre_label(genre))
    # Doppelte entfernen, Reihenfolge erhalten.
    seen = []
    for group in groups:
        if group and group not in seen:
            seen.append(group)
    return ';'.join(seen)


def _extinf(channel, url):
    attrs = [
        ('tvg-id', channel.get('epg_id') or channel['id']),
        ('tvg-name', channel['name']),
        ('tvg-country', (channel.get('country') or '').upper()),
        ('tvg-language', ' '.join(channel.get('language') or [])),
        ('tvg-logo', channel.get('logo') or ''),
        ('group-title', _groups(channel)),
    ]
    attr_str = ' '.join('%s="%s"' % (key, str(value).replace('"', "'")) for key, value in attrs)
    return '#EXTINF:-1 %s,%s\n%s\n' % (attr_str, channel['name'], url)


def generate(channels=None, direct=False):
    """Vollstaendige M3U als String. ``channels`` default = sichtbarer Katalog."""
    if channels is None:
        channels = catalog.visible_channels()
    else:
        channels = list(contentgate.filter_channels(channels))

    lines = ['#EXTM3U\n']
    # Fingerprint als Kommentar - hilft beim Debuggen und macht Aenderungen
    # der Sichtbarkeit im Export nachvollziehbar.
    lines.append('# gerxstream visibility=%s\n' % contentgate.visibility_fingerprint())
    for channel in channels:
        url = _direct_url(channel) if direct else _plugin_play_url(channel)
        if not url:
            continue
        lines.append(_extinf(channel, url))
    return ''.join(lines)
