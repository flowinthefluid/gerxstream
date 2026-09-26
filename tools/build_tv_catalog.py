# -*- coding: utf-8 -*-
"""Baut einen Live-TV-Katalog aus den Laenderlisten von iptv-org.

    python tools/build_tv_catalog.py de at ch --out resources/livestreams/sources/tv_dach.json

Aufgenommen werden nur Streams, die auf den Servern des Senders selbst oder
seines beauftragten Verbreiters liegen (Sender-CDN, Playout-Dienstleister,
FAST-Plattformen wie Rakuten TV oder Samsung TV Plus). Weiterverbreitungen
ueber fremde Server - rohe IP-Adressen, IPTV-Anbieter anderer Laender,
anonyme Restream-Hoster - fallen heraus. Private Sender wie RTL oder
ProSieben tauchen in diesen Listen nur so auf und sind deshalb nicht dabei.

Jeder Stream wird abgerufen. Aufgenommen wird, was eine gueltige Playlist
liefert, und zusaetzlich, was als geogesperrt markiert ist und mit 403
antwortet (funktioniert im jeweiligen Land). Alles andere wird verworfen.
"""

import argparse
import concurrent.futures
import datetime
import json
import re
import sys
import urllib.request
from urllib.parse import urlparse

SOURCE = 'https://iptv-org.github.io/iptv/countries/%s.m3u'
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/140.0 Safari/537.36')

# Weiterverbreiter ohne Senderbezug.
DENY_HOST_SUFFIXES = (
    'antik.sk', 'streamhostingcdn.top', 'freeott.top', 'dens.tv', 'livebox.co.in',
    'rtvpendimi.com', 'yoltv.com', 'goprimetime.info', 'jmp2.uk',
)
# In der EU sanktioniert (Verordnung (EU) 2022/350).
DENY_HOST_SUFFIXES += ('rttv.com',)
# Fremde Sendernamen auf Servern eines anderen Betreibers.
DENY_NAMES = (
    (re.compile(r'anixa\.tv$'), re.compile(r'^(?!anixe)', re.I)),
    (re.compile(r'streamlock\.net$'), re.compile(r'^srf\b', re.I)),
)

GENRE_MAP = {
    'news': 'news', 'sports': 'sports', 'kids': 'kids', 'animation': 'kids',
    'documentary': 'doc', 'music': 'music', 'movies': 'movies', 'series': 'series',
    'comedy': 'comedy', 'shop': 'shopping', 'culture': 'doc', 'education': 'doc',
    'outdoor': 'nature', 'travel': 'nature', 'science': 'doc', 'legislative': 'news',
    'lifestyle': 'series', 'entertainment': 'series', 'general': 'series',
    'religious': 'series', 'family': 'series', 'classic': 'movies', 'auto': 'series',
}

# Sport: Racing/Motorsport gehoert dazu, Baseball und American Football nicht.
RACING_NAMES = re.compile(r'red bull|motor|racing|rally|top gear|speed|drift|cycling|freesports|strongman', re.I)
EXCLUDED_NAMES = re.compile(r'\bnfl\b|american football|baseball|\bmlb\b|college football', re.I)

# Oeffentlich-rechtliche Sender erkennt man am Server, nicht am Namen.
PUBLIC_HOSTS = re.compile(
    r'(ard-mcdn\.de|\.br\.de|\.ndr\.de|mdn\.ors\.at|cdn\.tv1\.eu|^(zdf-hls|kikahls|hrhls|mdrtv|rbb-hls|'
    r'rbhlslive|srfs|srde|swr|wdr|tagesschau|artesimulcast|dwamdstream|ndrint|rtsinfo|'
    r'visualradio-rts)[^.]*\.akamaized\.net)$')

# iptv-org schreibt Umlaute aus.
UMLAUTS = (('Wurttemberg', 'Württemberg'), ('Dusseldorf', 'Düsseldorf'), ('Munster', 'Münster'),
           ('Thuringen', 'Thüringen'), ('Munchen', 'München'), ('Oberosterreich', 'Oberösterreich'),
           ('Kaernten', 'Kärnten'), ('Sudost', 'Südost'), ('Allgau', 'Allgäu'), (' Sud', ' Süd'),
           ('Weinstrasse', 'Weinstraße'), ('Niedersachen', 'Niedersachsen'))

# Sender-CDNs, die ausserhalb ihres Landes grundsaetzlich sperren.
GEO_HOSTS = ('mdn.ors.at',)

# Offizielle Streams, die in den iptv-org-Listen nur ueber Fremdserver stehen.
EXTRA = (
    ('de', 'ZDF', 'https://zdf-hls-15.akamaized.net/hls/live/2016498/de/high/master.m3u8', 'General', ''),
    ('de', 'ZDFneo', 'https://zdf-hls-16.akamaized.net/hls/live/2016499/de/high/master.m3u8', 'Series', ''),
    ('de', 'ZDFinfo', 'https://zdf-hls-17.akamaized.net/hls/live/2016500/de/high/master.m3u8', 'Documentary', ''),
    ('de', '3sat', 'https://zdf-hls-18.akamaized.net/hls/live/2016501/dach/high/master.m3u8', 'Culture', ''),
    ('de', 'phoenix', 'https://zdf-hls-19.akamaized.net/hls/live/2016502/de/high/master.m3u8', 'News', ''),
    ('de', 'DW Deutsch', 'https://dwamdstream106.akamaized.net/hls/live/2017965/dwstream106/index.m3u8', 'News', ''),
    ('de', 'WELT', 'https://welt.personalstream.tv/v1/master.m3u8?ads.country=de&ads.pf=welttv', 'News', ''),
    ('de', 'WELT', 'https://w-live2weltcms.akamaized.net/hls/live/2041019/Welt-LivePGM/index.m3u8', 'News', ''),
    ('de', 'Red Bull TV', 'https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8', 'Sports', ''),
    ('de', 'DW English', 'https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/index.m3u8', 'News', ''),
)


def _fetch(url, limit=65536, timeout=15):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(limit)
    except urllib.error.HTTPError as error:
        return error.code, b''
    except Exception:
        return 0, b''


def parse_m3u(country, text):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith('#EXTINF'):
            continue
        cursor = index + 1
        headers = {}
        while cursor < len(lines) and lines[cursor].startswith('#'):
            match = re.match(r'#EXTVLCOPT:http-(user-agent|referrer)=(.*)', lines[cursor])
            if match:
                headers['User-Agent' if match.group(1) == 'user-agent' else 'Referer'] = match.group(2).strip()
            cursor += 1
        if cursor >= len(lines):
            continue
        attrs = dict(re.findall(r'([a-z\-]+)="([^"]*)"', line))
        for key in ('http-user-agent', 'http-referrer'):
            if attrs.get(key):
                headers['User-Agent' if key == 'http-user-agent' else 'Referer'] = attrs[key]
        yield {
            'country': country,
            'label': line.rsplit(',', 1)[1].strip(),
            'url': lines[cursor].strip(),
            'group': attrs.get('group-title', ''),
            'logo': attrs.get('tvg-logo', ''),
            'epg_id': attrs.get('tvg-id', ''),
            'headers': headers,
        }


def allowed(entry):
    if EXCLUDED_NAMES.search(entry['label']):
        return False
    host = (urlparse(entry['url']).hostname or '').lower()
    if not host or re.fullmatch(r'[\d.]+', host) or ':' in host:
        return False
    if any(host == suffix or host.endswith('.' + suffix) for suffix in DENY_HOST_SUFFIXES):
        return False
    for hostPattern, namePattern in DENY_NAMES:
        if hostPattern.search(host) and namePattern.search(entry['label']):
            return False
    return urlparse(entry['url']).scheme in ('http', 'https')


def clean_name(label):
    name = re.sub(r'\s*\[(Geo-blocked|Not 24/7)\]', '', label)
    quality = re.search(r'\((\d{3,4})p\)', name)
    name = re.sub(r'\s*\(\d{3,4}p\)', '', name).strip()
    name = re.sub(r'^Red Bull TV\b.*', 'Red Bull TV', name)
    for plain, proper in UMLAUTS:
        name = re.sub(r'%s' % re.escape(plain) + r'\b', proper, name)
    return name, int(quality.group(1)) if quality else 0


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-') or 'x'


def verify(entry):
    status, body = _fetch(entry['url'])
    if status == 0:  # Zeitueberschreitung: einmal wiederholen
        status, body = _fetch(entry['url'], timeout=25)
    text = body.decode('utf-8', 'replace')
    playable = status == 200 and ('#EXTM3U' in text[:2048] or '<MPD' in text[:4096])
    geo = '[Geo-blocked]' in entry['label']
    host = urlparse(entry['url']).hostname or ''
    if host.endswith(GEO_HOSTS):
        # Liefert ausserhalb des Landes 403 oder nur eine Geoschutz-Tafel.
        return 'geo' if playable or status in (302, 401, 403, 451) else None
    if playable:
        return 'ok'
    if geo and status in (401, 403, 451):
        return 'geo'
    return None


def to_channel(entry, state, today):
    name, height = clean_name(entry['label'])
    groups = [g.strip().lower() for g in entry['group'].split(';') if g.strip()]
    genres = sorted(set(GENRE_MAP[g] for g in groups if g in GENRE_MAP)) or ['series']
    if PUBLIC_HOSTS.search(urlparse(entry['url']).hostname or ''):
        genres = sorted(set(genres) | {'public'})
    sports = 'sports' in genres or bool(RACING_NAMES.search(name))
    if sports:
        genres = sorted(set(genres) | {'sports'})
    if 'regional' not in genres and re.search(r'\b(tv|fernsehen|ok)\b', name, re.I) and 'regional' in groups:
        genres.append('regional')
    url = entry['url']
    source = {
        'source_id': '%s-%s' % (slug(name), 'dash' if '.mpd' in url else 'hls'),
        'url': url,
        'protocol': 'dash' if '.mpd' in url else 'hls',
        'quality': 'hd' if height >= 720 else ('sd' if height else 'unknown'),
        'official': True,
        'reliability': 'low' if '[Not 24/7]' in entry['label'] else 'medium',
        'region': entry['country'],
        'geo_restricted': state == 'geo' or '[Geo-blocked]' in entry['label'],
        'last_verified_at': today,
        'active': True,
    }
    if entry['headers']:
        source['headers'] = entry['headers']
    return {
        'id': 'gxs:%s:%s:%s' % ('sports' if sports else 'tv', entry['country'], slug(name)),
        'name': name,
        'section': 'sports' if sports else 'tv',
        'country': entry['country'],
        'language': ['de'] if entry['country'] in ('de', 'at') else [],
        'genre': genres,
        'nsfw': False,
        'publisher': slug(name),
        'logo': entry['logo'],
        'epg_id': entry['epg_id'],
        'sources': [source],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('countries', nargs='+')
    parser.add_argument('--out', required=True)
    parser.add_argument('--workers', type=int, default=16)
    args = parser.parse_args(argv)

    entries = []
    for country in args.countries:
        status, body = _fetch(SOURCE % country, limit=10 * 1024 * 1024, timeout=60)
        if status != 200:
            print('Liste fuer %s nicht ladbar (HTTP %s)' % (country, status))
            continue
        entries.extend(entry for entry in parse_m3u(country, body.decode('utf-8', 'replace')) if allowed(entry))
    for country, name, url, group, logo in EXTRA:
        if country in args.countries:
            entries.append({'country': country, 'label': name, 'url': url, 'group': group,
                            'logo': logo, 'epg_id': '', 'headers': {}})

    today = datetime.date.today().isoformat()
    channels = {}
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        for entry, state in zip(entries, pool.map(verify, entries)):
            if not state:
                print('  verworfen: %s (%s)' % (entry['label'], urlparse(entry['url']).hostname))
                continue
            channel = to_channel(entry, state, today)
            existing = channels.get(channel['id'])
            if existing:
                known = set(s['url'] for s in existing['sources'])
                for source in channel['sources']:
                    if source['url'] not in known:
                        source['source_id'] += '-%d' % (len(existing['sources']) + 1)
                        existing['sources'].append(source)
                existing['logo'] = existing['logo'] or channel['logo']
                existing['epg_id'] = existing['epg_id'] or channel['epg_id']
            else:
                channels[channel['id']] = channel

    ordered = sorted(channels.values(), key=lambda c: (c['country'], 'public' not in c['genre'], c['name'].lower()))
    with open(args.out, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump({'version': 1,
                   '_comment': 'Erzeugt mit tools/build_tv_catalog.py am %s aus iptv-org (%s). '
                               'Nur Streams auf Sender- bzw. Verbreiter-Servern; jeder Stream geprueft.'
                               % (today, ', '.join(args.countries)),
                   'channels': ordered}, handle, ensure_ascii=False, indent=1)
        handle.write('\n')
    print('%d Sender, %d Quellen -> %s' % (len(ordered), sum(len(c['sources']) for c in ordered), args.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
