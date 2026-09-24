# -*- coding: utf-8 -*-
"""EPG now/next: timezone-korrekt, TTL-Cache nach Mtime, fail-soft."""
import calendar
import os

from resources.lib.livestreams import epg

_GUIDE = os.path.join(os.path.dirname(__file__), 'fixtures', 'guide_sample.xml')


def _epoch(y, mo, d, h, mi):
    return calendar.timegm((y, mo, d, h, mi, 0, 0, 0, 0))


def test_parse_timezone_offset():
    # 11:00 +0100 entspricht 10:00 UTC.
    assert epg._parse_xmltv_epoch('20260924110000 +0100') == _epoch(2026, 9, 24, 10, 0)
    assert epg._parse_xmltv_epoch('20260924100000 +0000') == _epoch(2026, 9, 24, 10, 0)


def test_now_next_selects_current_and_following():
    # 10:30 UTC -> jetzt "Sendung A" (10-11), danach "Sendung B" (11-12).
    at = _epoch(2026, 9, 24, 10, 30)
    current, nxt = epg.now_next(_GUIDE, 'chan.de', at=at)
    assert current and current['title'] == 'Sendung A'
    assert nxt and nxt['title'] == 'Sendung B'


def test_now_next_unknown_channel_empty():
    at = _epoch(2026, 9, 24, 10, 30)
    assert epg.now_next(_GUIDE, 'does.not.exist', at=at) == (None, None)


def test_now_next_missing_file_failsoft():
    assert epg.now_next('/no/such/guide.xml', 'chan.de') == (None, None)
    assert epg.now_next_line('/no/such/guide.xml', 'chan.de') == ''


def test_cache_keyed_by_mtime(monkeypatch):
    epg._NOWNEXT_CACHE.update({'path': None, 'mtime': None, 'programmes': None})
    calls = {'n': 0}
    real_iterparse = epg.ET.iterparse

    def counting_iterparse(*a, **k):
        calls['n'] += 1
        return real_iterparse(*a, **k)

    monkeypatch.setattr(epg.ET, 'iterparse', counting_iterparse)
    at = _epoch(2026, 9, 24, 10, 30)
    epg.now_next(_GUIDE, 'chan.de', at=at)
    epg.now_next(_GUIDE, 'chan.de', at=at)
    # Zweiter Aufruf kommt aus dem Cache (gleiche Mtime) -> nur einmal geparst.
    assert calls['n'] == 1
