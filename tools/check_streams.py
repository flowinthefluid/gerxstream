#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA-Skript fuer den Livestream-Katalog (laeuft ohne Kodi).

- Schema-/Duplikat-/Rechte-Pruefung des kuratierten Katalogs (immer).
- Optional --check-network: prueft die Erreichbarkeit der freigegebenen
  http(s)-Quellen (HEAD, kurzer Timeout). rtsp/plugin werden uebersprungen.
- Optional --guide PATH: prueft eine XMLTV guide.xml auf Vollstaendigkeit
  (Anzahl Kanaele/Sendungen).

Reine Standardbibliothek + die Addon-Datenmodule (kein xbmc noetig).
"""

import argparse
import glob
import json
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from resources.lib.livestreams import model, verification  # noqa: E402


def _load_raw(sources_dir):
    raw = []
    for path in sorted(glob.glob(os.path.join(sources_dir, '*.json'))):
        try:
            data = json.load(open(path, encoding='utf-8'))
        except (OSError, ValueError) as exc:
            print('  ! %s nicht lesbar: %s' % (path, exc))
            continue
        channels = data.get('channels') if isinstance(data, dict) else data
        if isinstance(channels, list):
            raw.extend(channels)
    return raw


def _check_network(raw, timeout):
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
    ok = fail = skip = 0
    for channel in raw:
        cn = model.normalize_channel(channel)
        if not cn:
            continue
        for src in cn['sources']:
            url = src['url']
            if src['protocol'] in ('rtsp', 'rtmp', 'rtmpe', 'plugin'):
                skip += 1
                continue
            try:
                req = Request(url, method='HEAD', headers={'User-Agent': 'GerXStream-check/1.0'})
                with urlopen(req, timeout=timeout) as resp:
                    code = getattr(resp, 'status', 200)
                print('  OK  [%s] %s' % (code, url))
                ok += 1
            except HTTPError as e:
                # Manche Server lehnen HEAD ab (405) - dann als erreichbar werten.
                if e.code in (403, 405):
                    print('  OK? [%s] %s' % (e.code, url)); ok += 1
                else:
                    print('  FAIL [%s] %s' % (e.code, url)); fail += 1
            except (URLError, OSError) as e:
                print('  FAIL [%s] %s' % (e, url)); fail += 1
    print('Netzcheck: %d ok, %d fehlgeschlagen, %d uebersprungen' % (ok, fail, skip))
    return fail


def _check_guide(path):
    import xml.etree.ElementTree as ET
    channels = programmes = 0
    try:
        for _e, elem in ET.iterparse(path, events=('end',)):
            if elem.tag == 'channel':
                channels += 1
            elif elem.tag == 'programme':
                programmes += 1
            elem.clear()
    except (OSError, ET.ParseError) as exc:
        print('guide.xml Fehler: %s' % exc)
        return 1
    print('EPG: %d Kanaele, %d Sendungen' % (channels, programmes))
    return 0 if channels else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description='GerXStream Katalog-/Stream-Check')
    ap.add_argument('--dir', default=os.path.join(PROJECT_DIR, 'resources', 'livestreams', 'sources'))
    ap.add_argument('--check-network', action='store_true')
    ap.add_argument('--timeout', type=float, default=8.0)
    ap.add_argument('--guide')
    args = ap.parse_args(argv)

    raw = _load_raw(args.dir)
    report = verification.verify_channels(raw)
    print(verification.summarize(report))
    problems = len(report['invalid']) + len(report['duplicate_ids'])

    if args.check_network:
        problems += _check_network(raw, args.timeout)
    if args.guide:
        problems += _check_guide(args.guide)

    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
