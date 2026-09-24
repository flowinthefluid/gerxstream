# -*- coding: utf-8 -*-
# Python 3
"""XMLTV-EPG-Grabber, speicherschonend fuer TV-Boxen mit wenig RAM.

Design fuer 2-GB-Geraete:
  * Download als Stream, gzip/xz werden erkannt und dekomprimiert.
  * Parsing per ``ElementTree.iterparse`` mit ``elem.clear()`` - konstanter
    Speicher unabhaengig von der Dateigroesse (kein DOM im Heap).
  * Es werden NUR ``<channel>``- und ``<programme>``-Elemente uebernommen,
    deren ``channel``/``id`` zu einem sichtbaren Kanal gehoert, und nur
    Sendungen im Zeitfenster jetzt-2h .. jetzt+N.
  * Ergebnis wird als eine ``guide.xml`` gestreamt geschrieben.

Kein lxml (nicht in den Addon-Abhaengigkeiten) - reine Standardbibliothek.
"""

import gzip
import io
import lzma
import time
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

from resources.lib.tools import logger

_UA = 'Mozilla/5.0 (compatible; GerXStream-EPG/1.0)'
_XMLTV_TS = '%Y%m%d%H%M%S'


def _fetch(url, timeout=30):
    """Roh-Bytes einer EPG-Quelle holen und ggf. dekomprimieren."""
    request = Request(url, headers={'User-Agent': _UA, 'Accept-Encoding': 'gzip'})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        encoding = (response.headers.get('Content-Encoding') or '').lower()
    lower = url.lower()
    try:
        if lower.endswith('.xz') or raw[:6] == b'\xfd7zXZ\x00':
            return lzma.decompress(raw)
        if encoding == 'gzip' or lower.endswith('.gz') or raw[:2] == b'\x1f\x8b':
            return gzip.decompress(raw)
    except (OSError, lzma.LZMAError) as exc:
        logger.error('-> [livestreams.epg]: Dekompression fehlgeschlagen (%s): %s' % (url, exc))
        return b''
    return raw


def _parse_ts(value):
    """XMLTV-Zeitstempel 'YYYYMMDDHHMMSS +0000' -> epoch (grob, ohne TZ-Shift)."""
    if not value:
        return None
    core = value.strip().split(' ')[0][:14]
    try:
        return int(time.mktime(time.strptime(core, _XMLTV_TS)))
    except (ValueError, OverflowError):
        return None


def build_guide(source_urls, visible_epg_ids, out_path, window_hours=6):
    """Aus einer oder mehreren XMLTV-Quellen eine gefilterte guide.xml bauen.

    ``visible_epg_ids`` ist die Menge erlaubter Kanal-IDs (aus sichtbaren,
    NSFW-geprueften Kanaelen). Nur diese Kanaele und ihre Sendungen im
    Zeitfenster landen in der Ausgabe. Gibt die Zahl der Programme zurueck.
    """
    now = time.time()
    lower_bound = now - 2 * 3600
    upper_bound = now + window_hours * 3600
    allowed = set(visible_epg_ids or [])
    if not allowed:
        logger.info('-> [livestreams.epg]: keine sichtbaren Kanaele - EPG uebersprungen')
        return 0

    tmp_path = out_path + '.tmp'
    written = 0
    seen_channels = set()
    try:
        with open(tmp_path, 'w', encoding='utf-8') as out:
            out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            out.write('<tv generator-info-name="GerXStream">\n')

            for url in source_urls:
                data = _fetch(url)
                if not data:
                    continue
                try:
                    stream = io.BytesIO(data)
                    for event, elem in ET.iterparse(stream, events=('end',)):
                        tag = elem.tag
                        if tag == 'channel':
                            cid = elem.get('id')
                            if cid in allowed and cid not in seen_channels:
                                seen_channels.add(cid)
                                elem.tail = None
                                out.write(ET.tostring(elem, encoding='unicode').strip())
                                out.write('\n')
                            elem.clear()
                        elif tag == 'programme':
                            cid = elem.get('channel')
                            if cid in allowed:
                                start = _parse_ts(elem.get('start'))
                                if start is None or (lower_bound <= start <= upper_bound):
                                    elem.tail = None
                                    out.write(ET.tostring(elem, encoding='unicode').strip())
                                    out.write('\n')
                                    written += 1
                            elem.clear()
                except ET.ParseError as exc:
                    logger.error('-> [livestreams.epg]: XML-Fehler in %s: %s' % (url, exc))
                    continue

            out.write('</tv>\n')
        import os
        os.replace(tmp_path, out_path)
    except OSError as exc:
        logger.error('-> [livestreams.epg]: guide.xml nicht schreibbar: %s' % exc)
        return 0
    logger.info('-> [livestreams.epg]: %d Sendungen fuer %d Kanaele geschrieben'
                % (written, len(seen_channels)))
    return written


# ---------------------------------------------------------------------------
# In-Addon "jetzt / danach" aus der bereits gefilterten guide.xml.
# Fail-soft: jeder Fehler liefert leere Ergebnisse - EPG darf Navigation und
# Wiedergabe nie stoeren. TTL-Cache pro Datei-Mtime, timezone-korrekt.
# ---------------------------------------------------------------------------

import calendar
import os as _os

_NOWNEXT_CACHE = {'path': None, 'mtime': None, 'programmes': None}


def _parse_xmltv_epoch(value):
    """XMLTV-Zeit 'YYYYMMDDHHMMSS +0100' -> UTC-Epoch (tz-korrekt) oder None."""
    if not value:
        return None
    parts = value.strip().split(' ', 1)
    core = parts[0][:14]
    try:
        struct = time.strptime(core, _XMLTV_TS)
    except (ValueError, OverflowError):
        return None
    epoch = calendar.timegm(struct)  # als UTC interpretiert
    if len(parts) == 2 and parts[1]:
        sign = 1
        offset = parts[1].strip()
        if offset[0] in '+-':
            sign = -1 if offset[0] == '-' else 1
            offset = offset[1:]
        if len(offset) >= 4 and offset[:4].isdigit():
            epoch -= sign * (int(offset[:2]) * 3600 + int(offset[2:4]) * 60)
    return epoch


def _load_programmes(guide_path):
    """Programme aus guide.xml je Kanal, gecacht nach Datei-Mtime."""
    try:
        mtime = _os.path.getmtime(guide_path)
    except OSError:
        return {}
    if _NOWNEXT_CACHE['path'] == guide_path and _NOWNEXT_CACHE['mtime'] == mtime:
        return _NOWNEXT_CACHE['programmes']
    programmes = {}
    try:
        for _event, elem in ET.iterparse(guide_path, events=('end',)):
            if elem.tag == 'programme':
                cid = elem.get('channel')
                if cid:
                    title_el = elem.find('title')
                    title = title_el.text if title_el is not None else ''
                    programmes.setdefault(cid, []).append((
                        _parse_xmltv_epoch(elem.get('start')),
                        _parse_xmltv_epoch(elem.get('stop')),
                        title or '',
                    ))
                elem.clear()
    except (ET.ParseError, OSError) as exc:
        logger.error('-> [livestreams.epg]: now/next Parsing fehlgeschlagen: %s' % exc)
        return {}
    for cid in programmes:
        programmes[cid].sort(key=lambda p: (p[0] is None, p[0]))
    _NOWNEXT_CACHE.update({'path': guide_path, 'mtime': mtime, 'programmes': programmes})
    return programmes


def now_next(guide_path, epg_id, at=None):
    """(jetzt, danach) als EpgEntry-dicts fuer einen Sender, oder (None, None)."""
    if not epg_id:
        return (None, None)
    now = time.time() if at is None else at
    programmes = _load_programmes(guide_path).get(epg_id, [])
    current = nxt = None
    for start, stop, title in programmes:
        if start is None:
            continue
        if stop and start <= now < stop:
            current = {'title': title, 'start': start, 'stop': stop}
        elif start > now and nxt is None:
            nxt = {'title': title, 'start': start, 'stop': stop}
    return (current, nxt)


def now_next_line(guide_path, epg_id):
    """Menschliche 'Jetzt: ... | Danach: ...'-Zeile, oder '' (fail-soft)."""
    try:
        current, nxt = now_next(guide_path, epg_id)
    except Exception:
        return ''
    parts = []
    if current:
        parts.append('Jetzt: %s (%s)' % (current['title'], time.strftime('%H:%M', time.localtime(current['start']))))
    if nxt:
        parts.append('Danach: %s (%s)' % (nxt['title'], time.strftime('%H:%M', time.localtime(nxt['start']))))
    return '  |  '.join(parts)


def guide_timestamp(guide_path):
    """'Stand: ...' aus der Datei-Mtime, oder '' wenn keine guide.xml da ist."""
    try:
        return 'Stand: ' + time.strftime('%d.%m. %H:%M', time.localtime(_os.path.getmtime(guide_path)))
    except OSError:
        return ''
