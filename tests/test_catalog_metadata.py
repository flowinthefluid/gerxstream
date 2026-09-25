# -*- coding: utf-8 -*-
"""Abnahme Area 5: jede ausgelieferte, freigegebene Quelle traegt Betreiber,
Region, letzten Pruefzeitpunkt und eindeutige ID."""
import glob
import json
import os

from resources.lib.livestreams import model

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'resources', 'livestreams', 'sources')


def _shipped_channels():
    channels = []
    for path in sorted(glob.glob(os.path.join(_SRC, '*.json'))):
        data = json.load(open(path, encoding='utf-8'))
        for raw in (data.get('channels') or []):
            ch = model.normalize_channel(raw)
            if ch:
                channels.append(ch)
    return channels


def test_shipped_catalog_present():
    assert _shipped_channels(), 'kein Beispielkatalog ausgeliefert'


def test_approved_sources_have_full_metadata():
    for ch in _shipped_channels():
        approved = [s for s in ch['sources']
                    if s.get('active', True) and s['rights_status'] == model.RIGHTS_APPROVED]
        if not approved:
            continue  # bewusst ausgeschlossene (unknown) muessen es nicht haben
        assert ch['id'].startswith('gxs:'), ch['id']
        assert ch['publisher'], 'Betreiber fehlt: %s' % ch['id']
        region_ok = ch.get('country') or ch.get('region') or any(s.get('region') for s in approved)
        assert region_ok, 'Region fehlt: %s' % ch['id']
        assert any(s.get('last_verified_at') for s in approved) or ch.get('last_verified_at'), \
            'letzter Pruefzeitpunkt fehlt: %s' % ch['id']


def test_ids_unique_across_catalog():
    ids = [c['id'] for c in _shipped_channels()]
    assert len(ids) == len(set(ids)), 'doppelte Kanal-IDs im Katalog'
