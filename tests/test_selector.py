# -*- coding: utf-8 -*-
"""Tests fuer die Quellen-Reihenfolge (offiziell > Qualitaet > Zuverlaessigkeit)."""
from resources.lib.config import cConfig
from resources.lib.livestreams import selector


def _src(sid, official, quality, reliability):
    return {'source_id': sid, 'url': 'http://%s' % sid, 'protocol': 'hls',
            'quality': quality, 'official': official, 'reliability': reliability,
            'region': 'de', 'headers': {}}


def test_official_hd_wins():
    cConfig().setSetting('preferedQuality', '5')
    channel = {'id': 'c1', 'sources': [
        _src('unofficial-hd', False, 'hd', 'high'),
        _src('official-sd', True, 'sd', 'high'),
        _src('official-hd', True, 'hd', 'high'),
    ]}
    ordered = selector.order_sources(channel)
    assert ordered[0]['source_id'] == 'official-hd'


def test_recently_failed_goes_last(tmp_path, monkeypatch):
    import os
    monkeypatch.setenv('GXS_PROFILE', str(tmp_path))
    # Force selector to use the fresh profile dir.
    monkeypatch.setattr(selector, '_state_path',
                        lambda: os.path.join(str(tmp_path), 'health.json'))
    channel = {'id': 'c1', 'sources': [
        _src('a', True, 'hd', 'high'),
        _src('b', True, 'hd', 'high'),
    ]}
    selector.mark_failed('c1', 'a')
    ordered = selector.order_sources(channel)
    assert ordered[-1]['source_id'] == 'a'


def test_describe_reads_official_and_quality():
    text = selector.describe(_src('a', True, 'hd', 'high'))
    assert 'HD' in text
    assert 'stabil' in text
