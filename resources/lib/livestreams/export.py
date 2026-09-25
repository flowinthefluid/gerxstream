# -*- coding: utf-8 -*-
# Python 3
"""Export von playlist.m3u und guide.xml in den Nutzerordner.

Primaerweg fuer die IPTV-Simple-Anbindung: gefilterte Dateien liegen unter
``<profile>/livestreams/`` und der IPTV Simple Client wird auf diese lokalen
Dateien konfiguriert. Das ist der RAM-schonende Weg (kein Dauer-Thread, kein
lokaler HTTP-Server). Alle Schreibvorgaenge sind atomar.

Der Export laeuft ueber den sichtbaren Katalog - das Gate wirkt also auch
hier: bei NSFW=aus enthalten weder M3U noch EPG NSFW-Inhalte.
"""

import os
import time

from resources.lib.config import cConfig
from resources.lib.livestreams import catalog, m3u, epg
from resources.lib.tools import logger
from xbmcvfs import translatePath

# Wie oft der Service EPG/M3U hoechstens neu baut (Sekunden). Default 12h.
_DEFAULT_INTERVAL = 12 * 3600
_SETTING_LAST = 'lsLastRefresh'
_SETTING_INTERVAL_HOURS = 'lsRefreshHours'
_SETTING_EPG_URLS = 'lsEpgUrls'       # CSV mit XMLTV-Quellen (vom Nutzer)
_SETTING_EPG_WINDOW = 'lsEpgWindow'   # Stunden Vorschau
_SETTING_DIRECT = 'lsExportDirect'    # Direkt-URLs statt plugin://


def base_dir():
    profile = translatePath(cConfig().getAddonInfo('profile'))
    path = os.path.join(profile, 'livestreams')
    os.makedirs(path, exist_ok=True)
    return path


def playlist_path():
    return os.path.join(base_dir(), 'playlist.m3u')


def guide_path():
    return os.path.join(base_dir(), 'guide.xml')


def _atomic_write_text(path, text):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.replace(tmp, path)


def write_playlist():
    channels = catalog.visible_channels()
    direct = cConfig().getSettingBool(_SETTING_DIRECT, False)
    content = m3u.generate(channels, direct=direct)
    _atomic_write_text(playlist_path(), content)
    logger.info('-> [livestreams.export]: %d Kanaele nach %s' % (len(channels), playlist_path()))
    return len(channels)


def write_guide():
    urls = [u.strip() for u in (cConfig().getSetting(_SETTING_EPG_URLS, '') or '').split(',') if u.strip()]
    if not urls:
        logger.info('-> [livestreams.export]: keine EPG-Quellen konfiguriert')
        return 0
    visible_ids = set()
    for channel in catalog.visible_channels():
        visible_ids.add(channel.get('epg_id') or channel['id'])
    window = cConfig().getSettingInt(_SETTING_EPG_WINDOW, 6)
    return epg.build_guide(urls, visible_ids, guide_path(), window_hours=window)


def refresh(force=False):
    """Vom Service aufgerufen. Baut hoechstens alle N Stunden neu.

    Nie werfen - ein Fehler im Export darf den Kodi-Start nicht stoeren.
    """
    try:
        interval = max(1, cConfig().getSettingInt(_SETTING_INTERVAL_HOURS, 12)) * 3600
        last = cConfig().getSettingInt(_SETTING_LAST, 0)
        if not force and (time.time() - last) < interval:
            return False
        write_playlist()
        write_guide()
        cConfig().setSetting(_SETTING_LAST, str(int(time.time())))
        return True
    except Exception as exc:
        logger.error('-> [livestreams.export]: refresh fehlgeschlagen: %s' % exc)
        return False


def config_hint():
    """Menschlicher Hinweis fuer die gefuehrte IPTV-Simple-Einrichtung."""
    return (
        'IPTV Simple Client -> M3U Playlist URL:\n%s\n\n'
        'XMLTV EPG URL:\n%s'
    ) % (playlist_path(), guide_path())
