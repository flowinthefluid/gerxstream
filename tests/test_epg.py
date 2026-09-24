# -*- coding: utf-8 -*-
"""Tests fuer den XMLTV-Slicer: nur sichtbare Kanaele, konstanter Speicher."""
import os
import time

from resources.lib.livestreams import epg


def _sample():
    # Zeitstempel relativ zu jetzt, damit der Test nicht von der Uhrzeit
    # abhaengt (Sendung liegt sicher im Fenster now-2h .. now+window).
    start = time.strftime('%Y%m%d%H%M%S', time.gmtime(time.time() + 300))
    stop = time.strftime('%Y%m%d%H%M%S', time.gmtime(time.time() + 3600))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
        '  <channel id="ard.de"><display-name>Das Erste</display-name></channel>\n'
        '  <channel id="xxx.de"><display-name>XXX</display-name></channel>\n'
        '  <programme start="%s +0000" stop="%s +0000" channel="ard.de"><title>Tagesschau</title></programme>\n'
        '  <programme start="%s +0000" stop="%s +0000" channel="xxx.de"><title>Adult</title></programme>\n'
        '</tv>\n'
    ) % (start, stop, start, stop)


SAMPLE = _sample()


def test_guide_keeps_only_visible_channels(tmp_path, monkeypatch):
    # _fetch durch das Sample ersetzen, keine echten Netzzugriffe.
    monkeypatch.setattr(epg, '_fetch', lambda url, timeout=30: SAMPLE.encode('utf-8'))
    out = os.path.join(str(tmp_path), 'guide.xml')
    # Sehr weites Fenster, damit die Beispielzeit sicher hineinfaellt.
    written = epg.build_guide(['http://x'], {'ard.de'}, out, window_hours=24 * 3650)
    content = open(out, encoding='utf-8').read()
    assert 'ard.de' in content
    assert 'xxx.de' not in content
    assert 'Adult' not in content
    assert written >= 1


def test_empty_visible_set_skips(tmp_path, monkeypatch):
    monkeypatch.setattr(epg, '_fetch', lambda url, timeout=30: SAMPLE.encode('utf-8'))
    out = os.path.join(str(tmp_path), 'guide.xml')
    assert epg.build_guide(['http://x'], set(), out) == 0


def test_gzip_detected(monkeypatch):
    import gzip
    payload = gzip.compress(SAMPLE.encode('utf-8'))

    class _Resp:
        headers = {'Content-Encoding': ''}
        def read(self):
            return payload
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(epg, 'urlopen', lambda *a, **k: _Resp())
    data = epg._fetch('http://x/epg.xml.gz')
    assert b'<tv>' in data
