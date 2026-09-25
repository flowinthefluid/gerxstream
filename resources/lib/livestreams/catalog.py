# -*- coding: utf-8 -*-
# Python 3
"""Katalog: aggregiert Provider, validiert, mischt, entfernt Dubletten.

Der Source-Layer ist provider-basiert (siehe ``providers/base.py``): der
Standard-Provider ``curated`` liest die JSON-Kataloge unter
``resources/livestreams/sources/`` (mitgeliefert) und
``<profile>/livestreams/sources/`` (nutzereigen). Weitere Provider (APIs,
dokumentierte Feeds) lassen sich registrieren, ohne diese Kernlogik zu aendern.

Der Katalog wird pro Plugin-Aufruf einmal geladen und im Prozess gehalten
(jeder Kodi-Aufruf ist ohnehin ein frischer Prozess - kein Dauer-RAM). Das
Rendern eines Menues liest niemals das Netz; Netzzugriffe passieren nur im
Service (EPG) und beim Abspielen.

Dublettenlogik: Kanaele mit gleichem ``publisher`` und aehnlichem Namen
werden zu einem Kanal mit mehreren ``sources`` zusammengefasst.
"""

from resources.lib.livestreams import model
from resources.lib.livestreams.providers import base as providers
from resources.lib.tools import logger

_CACHE = {'key': None, 'channels': None}


def _merge_into(existing, channel, reason):
    """Zwei Kanaele zu einem mit mehreren Quellen zusammenfuehren (mit Log)."""
    known = {s['source_id'] for s in existing['sources']}
    added = 0
    for source in channel['sources']:
        if source['source_id'] not in known:
            existing['sources'].append(source)
            known.add(source['source_id'])
            added += 1
    # Eine gesetzte NSFW-Markierung darf nicht durch einen spaeteren
    # unmarkierten Eintrag verwaessert werden: konservativ bleiben.
    if existing.get('nsfw') is False and channel.get('nsfw') is None:
        existing['nsfw'] = None
    logger.info('-> [livestreams.catalog]: zusammengefuehrt %r <- %r (%s, +%d Quellen)'
                % (existing['id'], channel['id'], reason, added))


def _merge(channels):
    """Dubletten zusammenfuehren, unterschiedliche Blickwinkel aber behalten.

    Zusammengefuehrt wird nur bei belegter Identitaet: gleiche Kanal-ID,
    gleiche kanonische URL, oder gleiche (Sektion, Publisher, Name). Zwei
    verschiedene Ansichten desselben Betreibers (anderer Name/andere
    canonical_url) bleiben getrennt. Jede Zusammenfuehrung wird begruendet
    geloggt.
    """
    merged = []
    by_id = {}
    by_canon = {}
    by_triple = {}
    for channel in channels:
        cid = channel['id']
        canon = channel.get('canonical_url') or ''
        triple = (channel['section'], channel['publisher'], model.slugify(channel['name']))
        target = None
        reason = ''
        if cid in by_id:
            target, reason = by_id[cid], 'gleiche ID'
        elif canon and canon in by_canon:
            target, reason = by_canon[canon], 'gleiche canonical_url'
        elif triple in by_triple:
            target, reason = by_triple[triple], 'gleicher Publisher+Name'
        if target is not None:
            _merge_into(target, channel, reason)
            continue
        merged.append(channel)
        by_id[cid] = channel
        if canon:
            by_canon[canon] = channel
        by_triple[triple] = channel
    return merged


def _signature():
    return '|'.join(p.signature() for p in providers.registered_providers())


def load_all(force=False):
    """Alle Kanaele aller Provider (unabhaengig von Sichtbarkeit). Prozess-gecacht."""
    signature = _signature()
    if not force and _CACHE['key'] == signature and _CACHE['channels'] is not None:
        return _CACHE['channels']
    channels = []
    for provider in providers.registered_providers():
        try:
            raw_channels = provider.channels() or []
        except Exception as exc:
            logger.error('-> [livestreams.catalog]: Provider %s fehlgeschlagen: %s'
                         % (getattr(provider, 'id', '?'), exc))
            continue
        for raw in raw_channels:
            channel = model.normalize_channel(raw)
            if channel:
                channels.append(channel)
            else:
                logger.debug('-> [livestreams.catalog]: ungueltiger Kanal von %s verworfen'
                             % getattr(provider, 'id', '?'))
    channels = _merge(channels)
    _CACHE['key'] = signature
    _CACHE['channels'] = channels
    logger.info('-> [livestreams.catalog]: %d Kanaele geladen' % len(channels))
    return channels


# --- Rechte-Gate ----------------------------------------------------------

def approved_sources(channel):
    """Nur aktive Varianten mit belegter Rechtelage (fail-closed)."""
    from resources.lib.livestreams import model
    return [s for s in channel.get('sources', [])
            if s.get('active', True) and s.get('rights_status') == model.RIGHTS_APPROVED]


def _has_approved_source(channel):
    return len(approved_sources(channel)) > 0


# --- sichtbarkeitsgefilterte Sichten --------------------------------------

def visible_channels():
    """Standardkatalog: sichtbar (Gate) UND mit mindestens einer freigegebenen
    Quelle. Kanaele ohne belegte Rechtelage erscheinen hier nie.
    """
    from resources.lib import contentgate
    return [c for c in contentgate.filter_channels(load_all()) if _has_approved_source(c)]


def channels_by_section(section_id):
    return [c for c in visible_channels() if c['section'] == section_id]


def get_channel(channel_id):
    """Kanal nach ID - nur wenn sichtbar UND mit freigegebener Quelle.

    Das Gate und das Rechte-Gate greifen damit auch beim direkten Abspielen
    (Favorit, IPTV-Simple-plugin://-URL), nicht nur beim Rendern.
    """
    from resources.lib import contentgate
    for channel in load_all():
        if channel['id'] == channel_id:
            if contentgate.is_channel_visible(channel) and _has_approved_source(channel):
                return channel
            return None
    return None


def countries_in_section(section_id):
    seen = []
    for channel in channels_by_section(section_id):
        country = channel.get('country')
        if country and country not in seen:
            seen.append(country)
    return seen


def genres_in_section(section_id):
    seen = []
    for channel in channels_by_section(section_id):
        for genre in channel.get('genre') or []:
            if genre and genre not in seen:
                seen.append(genre)
    return seen
