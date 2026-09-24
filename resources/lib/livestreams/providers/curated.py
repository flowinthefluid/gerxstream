# -*- coding: utf-8 -*-
# Python 3
"""Kuratierter JSON-Katalog als Provider.

Liest ``resources/livestreams/sources/*.json`` (mitgeliefert) und
``<profile>/livestreams/sources/*.json`` (nutzereigen). Gibt rohe Kanal-dicts
zurueck; Validierung/Normalisierung macht ``catalog``/``model``.
"""

import json
import os

from resources.lib.config import cConfig
from resources.lib.livestreams.providers.base import Provider
from resources.lib.tools import logger
from xbmcvfs import translatePath


def bundle_dir():
    root = translatePath(cConfig().getAddonInfo('path'))
    return os.path.join(root, 'resources', 'livestreams', 'sources')


def user_dir():
    profile = translatePath(cConfig().getAddonInfo('profile'))
    return os.path.join(profile, 'livestreams', 'sources')


def _iter_json_files():
    for directory in (bundle_dir(), user_dir()):
        try:
            names = sorted(os.listdir(directory))
        except OSError:
            continue
        for name in names:
            if name.lower().endswith('.json'):
                yield os.path.join(directory, name)


class CuratedProvider(Provider):
    id = 'curated'

    def channels(self):
        result = []
        for path in _iter_json_files():
            try:
                with open(path, 'r', encoding='utf-8') as handle:
                    data = json.load(handle)
            except (OSError, ValueError) as exc:
                logger.error('-> [providers.curated]: %s nicht lesbar: %s' % (path, exc))
                continue
            channels = data.get('channels') if isinstance(data, dict) else data
            if isinstance(channels, list):
                result.extend(channels)
        return result

    def signature(self):
        stamps = []
        for path in _iter_json_files():
            try:
                stamps.append('%s:%s' % (path, int(os.path.getmtime(path))))
            except OSError:
                continue
        return 'curated|' + '|'.join(stamps)
