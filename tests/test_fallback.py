# -*- coding: utf-8 -*-
"""Fallback: naechste Quelle nur bei Fehlstart, Abbruch nach Erschoepfung."""
import sys

import pytest

# Ein Kanal mit zwei freigegebenen Varianten.
CHANNEL = {
    'id': 'gxs:webcam:us:c', 'name': 'Cam', 'section': 'webcam',
    'country': 'us', 'language': [], 'genre': [], 'nsfw': False,
    'publisher': 'p', 'logo': '', 'epg_id': '',
    'sources': [
        {'source_id': 's1', 'url': 'https://x/1.m3u8', 'protocol': 'hls',
         'quality': 'hd', 'official': True, 'reliability': 'high', 'region': 'us',
         'headers': {}, 'rights_status': 'approved', 'active': True, 'priority': 0},
        {'source_id': 's2', 'url': 'https://x/2.m3u8', 'protocol': 'hls',
         'quality': 'hd', 'official': True, 'reliability': 'high', 'region': 'us',
         'headers': {}, 'rights_status': 'approved', 'active': True, 'priority': 1},
    ],
}


@pytest.fixture
def route(monkeypatch):
    sys.argv = ['plugin://plugin.video.gerxstream/', '-1', '']
    from resources.lib.livestreams import route as r
    from resources.lib.livestreams import catalog, selector
    monkeypatch.setattr(catalog, 'get_channel', lambda cid: CHANNEL if cid == CHANNEL['id'] else None)
    monkeypatch.setattr(catalog, 'approved_sources', lambda ch: ch['sources'])
    fails, oks = [], []
    monkeypatch.setattr(selector, 'mark_failed', lambda c, s: fails.append(s))
    monkeypatch.setattr(selector, 'mark_ok', lambda c, s: oks.append(s))
    monkeypatch.setattr(r, '_notify', lambda *a, **k: None)
    r._test_fails, r._test_oks = fails, oks
    return r


def _mock_player(monkeypatch, route, results):
    """cPlayer.startPlayer liefert nacheinander die Werte aus results."""
    seq = iter(results)
    attempts = {'n': 0}

    class FakePlayer:
        def startPlayer(self):
            attempts['n'] += 1
            try:
                return next(seq)
            except StopIteration:
                return False

    import resources.lib.player as player
    monkeypatch.setattr(player, 'cPlayer', FakePlayer)
    return attempts


def _params(route, channel_id, source=None):
    from resources.lib.handler.ParameterHandler import ParameterHandler
    p = ParameterHandler()
    p.setParam('channel', channel_id)
    if source:
        p.setParam('source', source)
    return p


def test_fallback_tries_next_on_failure_then_stops(route, monkeypatch):
    attempts = _mock_player(monkeypatch, route, [False, False])
    route.play(_params(route, CHANNEL['id']))
    # Beide Quellen genau einmal versucht, dann Ende - keine Endlosschleife.
    assert attempts['n'] == 2
    assert route._test_fails == ['s1', 's2']
    assert route._test_oks == []


def test_success_stops_early(route, monkeypatch):
    attempts = _mock_player(monkeypatch, route, [True])
    route.play(_params(route, CHANNEL['id']))
    # Erste Quelle laeuft -> kein weiterer Versuch, kein Fehler vermerkt.
    assert attempts['n'] == 1
    assert route._test_oks == ['s1']
    assert route._test_fails == []


def test_forced_source_only_that_one(route, monkeypatch):
    attempts = _mock_player(monkeypatch, route, [False])
    route.play(_params(route, CHANNEL['id'], source='s2'))
    # Nur die erzwungene Quelle wird versucht.
    assert attempts['n'] == 1
    assert route._test_fails == ['s2']
