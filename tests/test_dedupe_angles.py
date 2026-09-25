# -*- coding: utf-8 -*-
"""Dublettenlogik: gleiche Identitaet mergen, verschiedene Blickwinkel behalten."""
from resources.lib.livestreams import model, catalog


def _raw(name, publisher, url, canonical='', cid=None):
    d = {'name': name, 'section': 'webcam', 'country': 'us', 'nsfw': False,
         'publisher': publisher, 'canonical_url': canonical,
         'sources': [{'url': url, 'official': True}]}
    if cid:
        d['id'] = cid
    return d


def test_same_canonical_url_merges():
    a = model.normalize_channel(_raw('Cam View', 'op', 'https://x/1', canonical='https://op/cam'))
    b = model.normalize_channel(_raw('Cam View 2', 'op', 'https://x/2', canonical='https://op/cam'))
    merged = catalog._merge([a, b])
    assert len(merged) == 1
    assert len(merged[0]['sources']) == 2


def test_different_angles_same_operator_kept_separate():
    # Gleicher Betreiber, verschiedene Namen und verschiedene canonical_url.
    a = model.normalize_channel(_raw('Harbour North', 'op', 'https://x/n', canonical='https://op/north'))
    b = model.normalize_channel(_raw('Harbour South', 'op', 'https://x/s', canonical='https://op/south'))
    merged = catalog._merge([a, b])
    assert len(merged) == 2


def test_same_id_merges():
    a = model.normalize_channel(_raw('A', 'op', 'https://x/1', cid='gxs:webcam:us:same'))
    b = model.normalize_channel(_raw('B', 'op', 'https://x/2', cid='gxs:webcam:us:same'))
    merged = catalog._merge([a, b])
    assert len(merged) == 1
    assert len(merged[0]['sources']) == 2
