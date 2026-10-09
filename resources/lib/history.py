# -*- coding: utf-8 -*-
"""Persistent, privacy-local playback history for GerXStream."""

import json
import os
import re
import time
from urllib.parse import parse_qsl, urlsplit

from xbmcvfs import translatePath

from resources.lib.config import cConfig


HISTORY_FILE = 'watch_history.json'
HISTORY_ENABLED_SETTING = 'watchHistoryEnabled'
HISTORY_LIMIT_SETTING = 'watchHistoryLimit'
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000
# 0 in der Einstellung bedeutet "unbegrenzt" (letzter Eintrag der Auswahl).
UNLIMITED = 0


def _clean(value, maximum=300):
    if not isinstance(value, str):
        value = str(value or '')
    return re.sub(r'\s+', ' ', value).strip()[:maximum]


def _historyPath():
    profile = translatePath(cConfig().getAddonInfo('profile'))
    if not os.path.isdir(profile):
        os.makedirs(profile)
    return os.path.join(profile, HISTORY_FILE)


def _limit():
    """Anzuzeigende Eintraege; None steht fuer unbegrenzt."""
    try:
        value = cConfig().getSettingInt(HISTORY_LIMIT_SETTING, DEFAULT_LIMIT)
    except Exception:
        return DEFAULT_LIMIT
    if value == UNLIMITED:
        return None
    return max(1, min(value, MAX_LIMIT))


def _storageLimit():
    """Gespeichert wird mindestens MAX_LIMIT, damit ein spaeter wieder
    hoeher gestelltes Limit keine Eintraege verloren hat."""
    limit = _limit()
    return None if limit is None else max(limit, MAX_LIMIT)


def _stored():
    """All valid stored entries, newest first; malformed data is ignored."""
    try:
        with open(_historyPath(), 'r', encoding='utf-8') as handle:
            stored = json.load(handle)
    except (IOError, OSError, ValueError, TypeError):
        return []
    if not isinstance(stored, list):
        return []
    valid = [entry for entry in stored if isinstance(entry, dict) and entry.get('title')]
    valid.sort(key=lambda entry: entry.get('watched_at', 0), reverse=True)
    return valid


def entries(limit=None):
    """Return newest entries first, capped by ``limit`` or the setting."""
    valid = _stored()
    if limit is None:
        limit = _limit()
    return valid if limit is None else valid[:limit]


def _save(entriesToSave):
    path = _historyPath()
    temporary = path + '.new'
    try:
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump(entriesToSave, handle, ensure_ascii=False, separators=(',', ':'))
        os.replace(temporary, path)
        return True
    except (IOError, OSError, TypeError, ValueError):
        try:
            if os.path.exists(temporary):
                os.unlink(temporary)
        except OSError:
            pass
    return False


def record(title, thumbnail='', mediaType='movie', source='', season='', episode='', showTitle='',
           target='', seriesTarget='', seriesTitle='', year='', targetIsFolder=False):
    """Store one successfully started playback without saving stream URLs."""
    from resources.lib import epicfavorites

    target = epicfavorites.normaliseTarget(target)
    seriesTarget = epicfavorites.normaliseTarget(seriesTarget)
    source = dict(parse_qsl(urlsplit(seriesTarget or target).query)).get('site') or source
    if target:
        epicfavorites.setStatus({'title': title, 'thumbnail': thumbnail, 'media_type': mediaType,
                                 'source': source, 'target': target, 'year': year,
                                 'series_target': seriesTarget,
                                 'series_title': seriesTitle or showTitle,
                                 'is_folder': targetIsFolder or mediaType in ('tvshow', 'season', 'episode')},
                                'watching', automatic=True)
    if not cConfig().getSettingBool(HISTORY_ENABLED_SETTING, True):
        return False
    title = _clean(title)
    showTitle = _clean(showTitle)
    searchTitle = showTitle or title
    if not title or not searchTitle:
        return False
    entry = {
        'title': title,
        'search_title': searchTitle,
        'thumbnail': _clean(thumbnail, 2000),
        'media_type': mediaType if mediaType in ('movie', 'tvshow', 'season', 'episode') else 'movie',
        'source': _clean(source, 100),
        'season': _clean(season, 20),
        'episode': _clean(episode, 20),
        'show_title': showTitle,
        'watched_at': int(time.time()),
        'target': target,
        'is_folder': targetIsFolder or mediaType in ('tvshow', 'season', 'episode'),
        'series_target': seriesTarget,
        'series_title': _clean(seriesTitle or showTitle),
        'year': _clean(year, 10),
    }
    key = (entry['search_title'].casefold(), entry['season'], entry['episode'])
    storageLimit = _storageLimit()
    previous = [item for item in _stored()
                if (str(item.get('search_title', '')).casefold(), str(item.get('season', '')),
                    str(item.get('episode', ''))) != key]
    if storageLimit is not None:
        previous = previous[:storageLimit - 1]
    return _save([entry] + previous)


def clear():
    """Erase only the locally stored playback history."""
    return _save([])
