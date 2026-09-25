# -*- coding: utf-8 -*-
# Python 3
"""Quellenauswahl, Beschreibung und Failover-Reihenfolge.

Trennt bewusst Katalogdaten (welche Quellen gibt es) von der Playback-Frage
(welche zuerst). Reihenfolge: zuletzt fehlgeschlagene ans Ende, offizielle vor
inoffiziellen, hoehere Qualitaet vor niedrigerer, hoehere Zuverlaessigkeit
zuerst - danach der Nutzerwunsch ``preferedQuality``.
"""

import json
import os
import time

from resources.lib.config import cConfig
from resources.lib.tools import logger
from xbmcvfs import translatePath

_QUALITY_RANK = {'uhd': 0, 'hd': 1, 'sd': 2, 'unknown': 3}
_RELIABILITY_RANK = {'high': 0, 'medium': 1, 'low': 2, 'unknown': 3}

# Wie lange eine gerade fehlgeschlagene Quelle ans Ende wandert (Sekunden).
_FAIL_PENALTY_WINDOW = 60 * 30


def _state_path():
    profile = translatePath(cConfig().getAddonInfo('profile'))
    return os.path.join(profile, 'livestreams', 'health.json')


def _load_state():
    try:
        with open(_state_path(), 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(state):
    path = _state_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump(state, handle)
        os.replace(tmp, path)
    except OSError as exc:
        logger.error('-> [livestreams.selector]: health.json nicht schreibbar: %s' % exc)


def mark_failed(channel_id, source_id):
    state = _load_state()
    state.setdefault(channel_id, {})[source_id] = {'failed': int(time.time())}
    _save_state(state)


def mark_ok(channel_id, source_id):
    state = _load_state()
    state.setdefault(channel_id, {})[source_id] = {'ok': int(time.time())}
    _save_state(state)


def _pref_quality_rank():
    # preferedQuality: 0..5 (240p..Best). >=3 gilt als HD-Wunsch.
    try:
        return 0 if cConfig().getSettingInt('preferedQuality', 5) >= 3 else 2
    except Exception:
        return 0


def order_sources(channel, sources=None):
    """Quellen eines Kanals in Abspiel-Reihenfolge (beste zuerst).

    ``sources`` erlaubt es, nur eine Teilmenge zu sortieren (z.B. nur
    rechtlich freigegebene Varianten). Reihenfolge zusaetzlich nach
    ``priority`` (kleinere Zahl zuerst).
    """
    candidates = channel.get('sources', []) if sources is None else sources
    state = _load_state().get(channel['id'], {})
    now = time.time()
    pref = _pref_quality_rank()

    def sort_key(source):
        health = state.get(source['source_id'], {})
        recently_failed = 1 if (now - health.get('failed', 0) < _FAIL_PENALTY_WINDOW) else 0
        official = 0 if source.get('official') else 1
        priority = source.get('priority', 0)
        quality = _QUALITY_RANK.get(source.get('quality'), 3)
        reliability = _RELIABILITY_RANK.get(source.get('reliability'), 3)
        # Abstand zum Qualitaetswunsch als leichte Zusatzsortierung.
        pref_gap = abs(quality - pref)
        return (recently_failed, priority, official, quality, reliability, pref_gap)

    return sorted(candidates, key=sort_key)


def describe(source):
    """Kurzbeschreibung wie 'Offiziell, HD, stabil' fuer die Auswahl-Liste."""
    kind = cConfig().getLocalizedString(31201) if source.get('official') else cConfig().getLocalizedString(31202)
    kind = kind if kind and not str(kind).startswith('#') else ('Offiziell' if source.get('official') else 'Inoffiziell')
    quality = {'uhd': '4K', 'hd': 'HD', 'sd': 'SD'}.get(source.get('quality'), '')
    reliability = {'high': 'stabil', 'medium': 'mittel', 'low': 'wackelig'}.get(source.get('reliability'), '')
    region = (source.get('region') or '').upper()
    parts = [p for p in (kind, quality, reliability, region) if p]
    return ', '.join(parts)


def best_source(channel):
    ordered = order_sources(channel)
    return ordered[0] if ordered else None
