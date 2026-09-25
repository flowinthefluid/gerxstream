# -*- coding: utf-8 -*-
"""Rabbithole-Session-Engine: zufaellig, ohne Wiederholung, filter-treu."""
from resources.lib.livestreams.rabbithole import RabbitholeSession, DictStore


def _session(ids, extra=''):
    return RabbitholeSession(lambda: list(ids), DictStore(), extra_sig=extra)


def test_no_repeat_until_exhausted():
    ids = ['a', 'b', 'c', 'd']
    s = _session(ids)
    seen = []
    for _ in range(len(ids)):
        cid = s.next()
        assert cid is not None
        seen.append(cid)
    # Alle genau einmal, keine Wiederholung.
    assert sorted(seen) == sorted(ids)
    assert len(set(seen)) == len(ids)


def test_exhaustion_returns_none():
    s = _session(['a', 'b'])
    assert s.next() is not None
    assert s.next() is not None
    assert s.next() is None            # erschoepft
    assert s.exhausted() is True


def test_reshuffle_makes_all_available_again():
    ids = ['a', 'b', 'c']
    s = _session(ids)
    while s.next() is not None:
        pass
    s.reshuffle()
    again = []
    cid = s.next()
    while cid is not None:
        again.append(cid)
        cid = s.next()
    assert sorted(again) == sorted(ids)


def test_empty_pool_returns_none():
    s = _session([])
    assert s.next() is None
    assert s.exhausted() is True


def test_filter_change_resets_session():
    store = DictStore()
    # Erst Pool A, danach anderer Pool (simuliert Filteraenderung via extra_sig).
    s1 = RabbitholeSession(lambda: ['a', 'b'], store, extra_sig='fp1')
    assert s1.next() is not None
    # Neuer Fingerprint -> Session beginnt neu, nichts "gesehen".
    s2 = RabbitholeSession(lambda: ['a', 'b'], store, extra_sig='fp2')
    assert s2.remaining() == 2


def test_pool_ids_are_only_from_provider():
    # Zufallsquelle ist ausschliesslich der uebergebene (gefilterte) Pool.
    ids = ['x', 'y']
    s = _session(ids)
    picks = {s.next() for _ in range(2)}
    assert picks <= set(ids)
