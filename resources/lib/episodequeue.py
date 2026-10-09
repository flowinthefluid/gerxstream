# -*- coding: utf-8 -*-
"""Kurzlebige Reihenfolge einer in Kodi angezeigten Episodenliste."""

import json
import os
import re
import time

from xbmcvfs import translatePath

from resources.lib.config import cConfig


STORAGE_FILE = 'episode_queues.json'
EPISODE_PLAYLIST_PROPERTY = 'GerXStream.EpisodePlaylist'
MAX_QUEUES = 30
MAX_AGE = 6 * 60 * 60


def _path():
    profile = translatePath(cConfig().getAddonInfo('profile'))
    if not os.path.isdir(profile):
        os.makedirs(profile)
    return os.path.join(profile, STORAGE_FILE)


def _load():
    try:
        with open(_path(), 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data):
    path = _path()
    temporary = path + '.new'
    try:
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(',', ':'))
        os.replace(temporary, path)
        return True
    except (IOError, OSError, TypeError, ValueError):
        try:
            if os.path.exists(temporary):
                os.unlink(temporary)
        except OSError:
            pass
    return False


def _validQueueId(value):
    return isinstance(value, str) and re.fullmatch(r'[a-f0-9]{16,32}', value)


def _validTarget(value):
    return isinstance(value, str) and value.startswith('plugin://plugin.video.gerxstream/')


def _prune(data, now=None):
    now = int(now or time.time())
    valid = {}
    for queueId, queue in data.items():
        if not _validQueueId(queueId) or not isinstance(queue, dict):
            continue
        created = int(queue.get('created_at') or 0)
        targets = queue.get('targets')
        if now - created > MAX_AGE or not isinstance(targets, list):
            continue
        targets = [target for target in targets if _validTarget(target)]
        if targets:
            valid[queueId] = {'created_at': created, 'targets': targets[:500]}
    newest = sorted(valid.items(), key=lambda item: item[1]['created_at'], reverse=True)
    return dict(newest[:MAX_QUEUES])


def store(queueId, targets):
    """Persist exactly the generated plugin routes of one episode directory."""
    if not _validQueueId(queueId):
        return False
    cleaned = [target for target in targets if _validTarget(target)]
    if not cleaned:
        return False
    data = _prune(_load())
    data[queueId] = {'created_at': int(time.time()), 'targets': cleaned[:500]}
    return _save(_prune(data))


def getTargets(queueId):
    """Return a copy of one current episode directory's plugin routes."""
    if not _validQueueId(queueId):
        return []
    data = _prune(_load())
    queue = data.get(queueId, {})
    targets = queue.get('targets', [])
    _save(data)  # Opportunistically discard expired entries.
    return list(targets) if isinstance(targets, list) else []
