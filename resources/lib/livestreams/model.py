# -*- coding: utf-8 -*-
# Python 3
"""Kanal- und Quellen-Datenmodell mit strenger, fail-closed Validierung.

Kanaele werden als schlichte ``dict``s gefuehrt (leicht (de)serialisierbar
und identisch mit dem, was das Gate erwartet). Dieses Modul stellt Bau,
Validierung und Normalisierung bereit. Ungueltige Datensaetze werden
verworfen (``None``), nicht repariert - so kann ein defekter Katalog keine
halbgaren Eintraege ins Menue spuelen.
"""

import re

from resources.lib.livestreams import taxonomy

_SLUG_RE = re.compile(r'[^a-z0-9]+')

VALID_PROTOCOLS = ('hls', 'dash', 'mp4', 'rtmp', 'rtsp', 'mjpeg', 'jpeg', 'plugin')
VALID_QUALITY = ('uhd', 'hd', 'sd', 'unknown')
VALID_RELIABILITY = ('high', 'medium', 'low', 'unknown')

# Rechte-Status einer Variante. Fail-closed: alles ausser 'approved' bleibt aus
# dem Standardkatalog fern (siehe catalog.approved_channels).
RIGHTS_APPROVED = 'approved'
RIGHTS_UNKNOWN = 'unknown'


def compute_rights_status(official, rights_evidence_url, drm, login_required):
    """Eine Variante gilt nur als freigegeben, wenn ihre Rechtelage belegt ist.

    'approved' erfordert eine offizielle Quelle ODER einen Freigabe-Nachweis
    (rights_evidence_url) UND darf weder DRM noch Login verlangen - beides
    unterstuetzt das Addon fuer diesen Bereich nicht und wird nicht umgangen.
    Alles andere -> 'unknown' und damit ausserhalb des Standardkatalogs.
    """
    if drm or login_required:
        return RIGHTS_UNKNOWN
    if official or rights_evidence_url:
        return RIGHTS_APPROVED
    return RIGHTS_UNKNOWN


def slugify(value):
    value = _SLUG_RE.sub('-', (value or '').strip().lower()).strip('-')
    return value or 'x'


# Erlaubte URL-Schemata fuer Stream-Quellen. Alles andere (javascript:, data:,
# file: ...) wird als ungueltig verworfen (fail-closed).
_ALLOWED_SCHEMES = ('http', 'https', 'rtsp', 'rtmp', 'rtmpe', 'plugin')


def is_valid_stream_url(url):
    """True, wenn die URL ein erlaubtes Schema und einen Host/Pfad hat."""
    from urllib.parse import urlparse
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
    except (ValueError, AttributeError):
        return False
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False
    # plugin:// braucht einen Addon-Host, alles andere einen Netzhost.
    if parsed.scheme == 'plugin':
        return bool(parsed.netloc)
    return bool(parsed.netloc)


# Reservierte Beispiel-/Dokumentationsziele (RFC 2606 / RFC 5737) und typische
# Platzhaltermarker. Quellen mit solchen Zielen duerfen nie AKTIV im Katalog
# landen - sie werden bei der Normalisierung zwangsweise deaktiviert.
_PLACEHOLDER_HOST_SUFFIXES = ('.example', '.example.com', '.example.net',
                              '.example.org', '.example.edu')
_PLACEHOLDER_HOSTS = ('example.com', 'example.net', 'example.org',
                      'example.edu', 'example.gov', 'localhost')
_PLACEHOLDER_IP_PREFIXES = ('203.0.113.', '198.51.100.', '192.0.2.',
                            '127.0.0.1')
_PLACEHOLDER_MARKERS = ('example', 'UC_EXAMPLE', 'CHANGEME', 'YOUR_', 'placeholder')


def is_placeholder_url(url):
    """True, wenn die URL auf ein reserviertes Beispiel-/Platzhalterziel zeigt."""
    from urllib.parse import urlparse
    if not url or not isinstance(url, str):
        return False
    host = (urlparse(url).hostname or '').lower()
    if host in _PLACEHOLDER_HOSTS:
        return True
    if any(host.endswith(suf) for suf in _PLACEHOLDER_HOST_SUFFIXES):
        return True
    if any(host.startswith(pref) for pref in _PLACEHOLDER_IP_PREFIXES):
        return True
    # Marker im gesamten URL (z.B. plugin://…UC_EXAMPLE).
    return any(marker in url for marker in _PLACEHOLDER_MARKERS)


def build_channel_id(section, country, name, publisher=''):
    # Name IMMER einbeziehen, damit verschiedene Blickwinkel desselben
    # Betreibers nicht auf dieselbe ID kollabieren (Dubletten-Fehlmerge).
    base = ('%s-%s' % (publisher, name)) if publisher else name
    return 'gxs:%s:%s:%s' % (slugify(section), slugify(country or 'int'), slugify(base))


def normalize_source(raw):
    """Eine Quelle validieren/normalisieren. Ungueltig -> None."""
    if not isinstance(raw, dict):
        return None
    url = (raw.get('url') or '').strip()
    if not url or not is_valid_stream_url(url):
        return None
    protocol = (raw.get('protocol') or '').lower()
    if protocol not in VALID_PROTOCOLS:
        # Aus der URL ableiten, sonst als Fehler behandeln.
        if url.startswith('plugin://'):
            protocol = 'plugin'
        elif '.m3u8' in url:
            protocol = 'hls'
        elif '.mpd' in url:
            protocol = 'dash'
        else:
            protocol = 'mp4'
    quality = (raw.get('quality') or 'unknown').lower()
    if quality not in VALID_QUALITY:
        quality = 'unknown'
    reliability = (raw.get('reliability') or 'unknown').lower()
    if reliability not in VALID_RELIABILITY:
        reliability = 'unknown'
    headers = raw.get('headers')
    if not isinstance(headers, dict):
        headers = {}
    official = bool(raw.get('official', False))
    rights_evidence_url = (raw.get('rights_evidence_url') or '').strip()
    drm = bool(raw.get('drm', False))
    login_required = bool(raw.get('login_required', False))
    # Platzhalter-/Beispielziele koennen nie aktiv werden (fail-closed).
    active = bool(raw.get('active', True)) and not is_placeholder_url(url)
    return {
        'source_id': str(raw.get('source_id') or slugify(url)),
        'provider_id': str(raw.get('provider_id') or raw.get('provider') or ''),
        'publisher': str(raw.get('publisher') or ''),
        'display_name': str(raw.get('display_name') or ''),
        'url': url,
        'protocol': protocol,
        'quality': quality,
        'official': official,
        'reliability': reliability,
        'region': (raw.get('region') or raw.get('country') or '').lower(),
        'language': [str(l).lower() for l in (raw.get('language') or []) if l],
        'headers': {str(k): str(v) for k, v in headers.items()},
        # --- Rechte / Verifikation (fail-closed) ---
        'drm': drm,
        'login_required': login_required,
        'geo_restricted': bool(raw.get('geo_restricted', False)),
        'rights_evidence_url': rights_evidence_url,
        'rights_status': compute_rights_status(official, rights_evidence_url, drm, login_required),
        'last_verified_at': (raw.get('last_verified_at') or '').strip(),
        'priority': int(raw.get('priority', 0)) if str(raw.get('priority', '')).lstrip('-').isdigit() else 0,
        'active': active,
    }


def normalize_channel(raw):
    """Einen Kanal validieren/normalisieren. Ungueltig -> None (fail-closed)."""
    if not isinstance(raw, dict):
        return None
    name = (raw.get('name') or '').strip()
    if not name:
        return None
    section = (raw.get('section') or '').lower()
    if not taxonomy.is_known_section(section):
        return None

    sources = []
    for raw_source in (raw.get('sources') or []):
        source = normalize_source(raw_source)
        if source:
            sources.append(source)
    if not sources:
        # Ein Kanal ohne abspielbare Quelle ist nutzlos.
        return None

    country = (raw.get('country') or 'int').lower()
    languages = [str(l).lower() for l in (raw.get('language') or []) if l]
    genres = [str(g).lower() for g in (raw.get('genre') or []) if g]

    # nsfw MUSS explizit bool sein; alles andere -> None, damit das Gate
    # fail-closed greifen kann (siehe contentgate._channel_is_nsfw).
    nsfw = raw.get('nsfw', None)
    if not isinstance(nsfw, bool):
        nsfw = None

    publisher = (raw.get('publisher') or '').strip()
    channel_id = (raw.get('id') or '').strip() or build_channel_id(section, country, name, publisher)

    return {
        'id': channel_id,
        'name': name,
        'section': section,
        'country': country,
        'region': (raw.get('region') or '').strip().lower(),
        'city': (raw.get('city') or '').strip(),
        'language': languages,
        'genre': genres,
        'nsfw': nsfw,
        'publisher': publisher or slugify(name),
        # Kanonische URL/ID fuer nachvollziehbare Dublettenzusammenfuehrung.
        'canonical_url': (raw.get('canonical_url') or '').strip(),
        'logo': (raw.get('logo') or '').strip(),
        'epg_id': (raw.get('epg_id') or '').strip(),
        'last_verified_at': (raw.get('last_verified_at') or '').strip(),
        'sources': sources,
    }
