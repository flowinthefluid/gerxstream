# -*- coding: utf-8 -*-
"""Bewertungen, Regie und Darsteller unter der Beschreibung.

Skins zeigen neben dem Cover meist nur die Beschreibung (Plot). Damit IMDb-
und Rotten-Tomatoes-Wertung sowie Regie und Darsteller in jeder Ansicht
sichtbar sind, werden sie als kurze Zeilen an die Beschreibung angehaengt und
zusaetzlich als Kodi-Wertungen gesetzt (fuer Skins, die diese selbst zeigen).

IMDb und Rotten Tomatoes kommen von OMDb (omdbapi.com) und brauchen einen
eigenen, kostenlosen API-Schluessel. Ohne Schluessel bleibt es bei TMDB-
Wertung, Regie und Darstellern.
"""

import json
import re

from resources.lib.config import cConfig


ENABLED_SETTING = 'plotExtras'
OMDB_KEY_SETTING = 'omdbApiKey'
OMDB_URL = 'https://www.omdbapi.com/?i=%s&apikey=%s'
MAX_ACTORS = 5


def enabled():
    return cConfig().getSettingBool(ENABLED_SETTING, False)


def _number(value):
    try:
        return float(str(value).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def parseOmdb(data):
    """{'imdb': (wertung, stimmen), 'rottentomatoes': '92%', 'metacritic': '82'}"""
    result = {}
    if not isinstance(data, dict) or data.get('Response') == 'False':
        return result
    rating = _number(data.get('imdbRating'))
    if rating:
        votes = re.sub(r'[^0-9]', '', str(data.get('imdbVotes') or ''))
        result['imdb'] = (rating, int(votes) if votes else 0)
    for entry in data.get('Ratings') or []:
        if not isinstance(entry, dict):
            continue
        source = str(entry.get('Source') or '')
        value = str(entry.get('Value') or '').strip()
        if source == 'Rotten Tomatoes' and re.fullmatch(r'\d{1,3}%', value):
            result['rottentomatoes'] = value
        elif source == 'Metacritic' and re.fullmatch(r'\d{1,3}/100', value):
            result['metacritic'] = value.split('/')[0]
    return result


def omdbRatings(imdbId):
    """IMDb-/RT-Wertungen per OMDb; leer ohne Schluessel oder bei Fehlern."""
    apiKey = (cConfig().getSetting(OMDB_KEY_SETTING) or '').strip()
    if not apiKey or not re.fullmatch(r'tt\d{5,10}', str(imdbId or '')):
        return {}
    if not re.fullmatch(r'[A-Za-z0-9]{4,40}', apiKey):
        return {}
    from resources.lib.handler.requestHandler import cRequestHandler
    # GET-Antworten landen im normalen HTML-Cache; das schont das Tageslimit.
    handler = cRequestHandler(OMDB_URL % (imdbId, apiKey), ignoreErrors=True, allow_insecure_tls=False)
    try:
        return parseOmdb(json.loads(handler.request() or '{}'))
    except (TypeError, ValueError):
        return {}


def minimumRating(setting):
    return max(0.0, min(cConfig().getSettingNumber(setting, 0.0), 10.0))


def requireImdbKey(minimum):
    if not minimum:
        return True
    if re.fullmatch(r'[A-Za-z0-9]{4,40}', cConfig().getSetting(OMDB_KEY_SETTING).strip()):
        return True
    from resources.lib.gui.gui import cGui
    cGui().showInfo('GerXStream', cConfig().getLocalizedString(31710))
    return False


def matchesMinimum(item, media, minimum):
    if not minimum:
        return True
    from resources.lib.tmdb import cTMDB

    imdb_id = item.get('imdb_id')
    if not imdb_id:
        tmdb_id = item.get('id')
        if not str(tmdb_id or '').isdigit() or media not in ('movie', 'tv'):
            return False
        external = cTMDB().getUrl('%s/%s/external_ids' % (media, tmdb_id)) or {}
        imdb_id = external.get('imdb_id')
    rating = (omdbRatings(imdb_id).get('imdb') or (0, 0))[0]
    return minimum <= rating <= 10


def _actors(meta):
    names = []
    for entry in meta.get('cast') or []:
        name = entry[0] if isinstance(entry, (list, tuple)) and entry else ''
        if name and name not in names:
            names.append(name)
        if len(names) >= MAX_ACTORS:
            break
    return names


def buildLines(meta, ratings=None, mediaType='movie'):
    """Die anzuhaengenden Zeilen (ohne Leerzeile davor)."""
    ratings = ratings or {}
    parts = []
    if 'imdb' in ratings:
        parts.append('[B]IMDb[/B] %.1f' % ratings['imdb'][0])
    if 'rottentomatoes' in ratings:
        parts.append('[B]Rotten Tomatoes[/B] %s' % ratings['rottentomatoes'])
    if 'metacritic' in ratings:
        parts.append('[B]Metacritic[/B] %s' % ratings['metacritic'])
    tmdbRating = _number(meta.get('rating'))
    if tmdbRating:
        parts.append('[B]TMDB[/B] %.1f' % tmdbRating)
    lines = []
    if parts:
        lines.append('  ·  '.join(parts))
    director = str(meta.get('director') or '').strip()
    if director:
        lines.append('[B]%s:[/B] %s' % (cConfig().getLocalizedString(31461), director))
    elif mediaType == 'tvshow' and meta.get('creator'):
        lines.append('[B]%s:[/B] %s' % (cConfig().getLocalizedString(31462), meta['creator']))
    actors = _actors(meta)
    if actors:
        lines.append('[B]%s:[/B] %s' % (cConfig().getLocalizedString(31463), ', '.join(actors)))
    return lines


def appendTo(plot, lines):
    plot = (plot or '').strip()
    if not lines:
        return plot
    return (plot + '\n\n' if plot else '') + '\n'.join(lines)
