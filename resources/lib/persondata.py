# -*- coding: utf-8 -*-
"""Filmanzahl und Auszeichnungen beliebter Personen aus Wikidata.

TMDB kennt weder Oscars noch Grammys, und die Filmanzahl je Person kostet dort
eine Anfrage pro Person. Wikidata beantwortet beides fuer bis zu 150 Personen
in einer einzigen Abfrage, verknuepft ueber die TMDB-Personen-ID (P4985).

Die Werte sind Gemeinschaftsdaten und nicht immer vollstaendig. Fuer die
Sortierung einer Liste reicht das; Fehler oder Zeitueberschreitungen fuehren
nie zu einer leeren Liste, sondern nur dazu, dass nach Popularitaet sortiert
bleibt.
"""

import json
import os
import re
import time

from resources.lib.config import cConfig
from resources.lib.tools import logger


ENDPOINT = 'https://query.wikidata.org/sparql'
CACHE_FILE = 'person_counts.json'
CACHE_MAX_AGE = 14 * 24 * 60 * 60
BATCH_SIZE = 150

# Wikidata-Klassen: Academy Awards und Grammy Award. Jede Kategorie ("Bester
# Hauptdarsteller") ist eine Instanz davon; gezaehlt werden die einzelnen
# Aussagen, damit zwei Oscars in derselben Kategorie auch zwei ergeben.
OSCAR = 'Q19020'
GRAMMY = 'Q41254'
FILM = 'Q11424'
# Darsteller (P161) bzw. Regie (P57)
ROLE_PROPERTY = {'Acting': 'P161', 'Directing': 'P57'}

_QUERY = '''SELECT ?tmdb ?kind (COUNT(DISTINCT ?x) AS ?n) WHERE {
  VALUES ?tmdb { %(ids)s }
  ?p wdt:P4985 ?tmdb .
  { ?x wdt:%(role)s ?p . ?x wdt:P31 wd:%(film)s . BIND("films" AS ?kind) }
  UNION { ?p p:P166 ?x . ?x ps:P166/wdt:P31 wd:%(oscar)s . BIND("oscars" AS ?kind) }
  UNION { ?p p:P166 ?x . ?x ps:P166/wdt:P31 wd:%(grammy)s . BIND("grammys" AS ?kind) }
} GROUP BY ?tmdb ?kind'''


def _cachePath():
    from xbmcvfs import translatePath
    profile = translatePath(cConfig().getAddonInfo('profile'))
    if not os.path.isdir(profile):
        os.makedirs(profile)
    return os.path.join(profile, CACHE_FILE)


def _loadCache():
    try:
        with open(_cachePath(), 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _saveCache(data):
    path = _cachePath()
    temporary = path + '.new'
    try:
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, separators=(',', ':'))
        os.replace(temporary, path)
    except (IOError, OSError, TypeError, ValueError):
        pass


def _cacheKey(role, personId):
    return '%s:%s' % ('d' if role == 'Directing' else 'a', personId)


def buildQuery(personIds, role='Acting'):
    ids = ' '.join('"%d"' % int(personId) for personId in personIds)
    return _QUERY % {'ids': ids, 'role': ROLE_PROPERTY.get(role, 'P161'),
                     'film': FILM, 'oscar': OSCAR, 'grammy': GRAMMY}


def parseResult(payload):
    """{tmdb_id: {'films': n, 'oscars': n, 'grammys': n}} aus der SPARQL-Antwort."""
    counts = {}
    try:
        rows = payload['results']['bindings']
    except (KeyError, TypeError):
        return counts
    for row in rows:
        try:
            personId = str(int(row['tmdb']['value']))
            kind = row['kind']['value']
            value = int(row['n']['value'])
        except (KeyError, TypeError, ValueError):
            continue
        if kind in ('films', 'oscars', 'grammys'):
            counts.setdefault(personId, {})[kind] = value
    return counts


def _request(query):
    from resources.lib.handler.requestHandler import cRequestHandler
    handler = cRequestHandler(ENDPOINT, caching=False, ignoreErrors=True, method='POST',
                              data={'query': query, 'format': 'json'}, allow_insecure_tls=False)
    # Wikidata verlangt einen erkennbaren User-Agent statt eines Browser-UA.
    handler.addHeaderEntry('User-Agent', 'GerXStream/%s (Kodi add-on; people sorting)'
                           % cConfig().getAddonInfo('version'))
    handler.addHeaderEntry('Accept', 'application/sparql-results+json')
    handler.requestTimeout = max(handler.requestTimeout, 30)
    try:
        return json.loads(handler.request() or '{}')
    except (TypeError, ValueError):
        return {}


def counts(personIds, role='Acting'):
    """Filmanzahl und Auszeichnungen fuer TMDB-Personen (gecacht, 14 Tage)."""
    wanted = []
    for personId in personIds:
        if re.fullmatch(r'\d+', str(personId or '')):
            wanted.append(str(personId))
    cache = _loadCache()
    now = int(time.time())
    result = {}
    missing = []
    for personId in wanted:
        entry = cache.get(_cacheKey(role, personId))
        if isinstance(entry, dict) and now - int(entry.get('ts', 0)) < CACHE_MAX_AGE:
            result[personId] = entry
        else:
            missing.append(personId)
    changed = False
    for start in range(0, len(missing), BATCH_SIZE):
        batch = missing[start:start + BATCH_SIZE]
        payload = _request(buildQuery(batch, role))
        if not payload:
            logger.info('-> [persondata]: Wikidata nicht erreichbar, Sortierung bleibt unvollstaendig')
            break
        found = parseResult(payload)
        for personId in batch:
            entry = dict(found.get(personId, {}))
            entry.setdefault('films', 0)
            entry.setdefault('oscars', 0)
            entry.setdefault('grammys', 0)
            entry['ts'] = now
            cache[_cacheKey(role, personId)] = entry
            result[personId] = entry
            changed = True
    if changed:
        # Abgelaufene Eintraege beim Schreiben gleich mit entfernen.
        cache = dict((key, value) for key, value in cache.items()
                     if isinstance(value, dict) and now - int(value.get('ts', 0)) < CACHE_MAX_AGE)
        _saveCache(cache)
    return result


def productionGroups(countries):
    mapping = {'US': 'hollywood', 'DE': 'german', 'JP': 'japanese',
               'KR': 'korean', 'IN': 'indian'}
    return {mapping.get(country.upper(), 'other') for country in countries if country}


def filmProfiles(personIds, role='Acting'):
    wanted = list(dict.fromkeys(str(personId) for personId in personIds
                                if re.fullmatch(r'\d+', str(personId or ''))))
    cache = _loadCache()
    now = int(time.time())
    result = {}
    missing = []
    for personId in wanted:
        entry = cache.get('profile:' + _cacheKey(role, personId))
        if isinstance(entry, dict) and now - int(entry.get('ts', 0)) < CACHE_MAX_AGE:
            result[personId] = entry
        else:
            missing.append(personId)
    changed = False
    for start in range(0, len(missing), BATCH_SIZE):
        batch = missing[start:start + BATCH_SIZE]
        query = '''SELECT DISTINCT ?tmdb ?country ?imdb WHERE {
  VALUES ?tmdb { %s }
  ?person wdt:P4985 ?tmdb .
  ?film wdt:%s ?person ; wdt:P31/wdt:P279* wd:Q11424 .
  OPTIONAL { ?film wdt:P495/wdt:P297 ?country . }
  OPTIONAL { ?film wdt:P345 ?imdb . }
}''' % (' '.join('"%s"' % personId for personId in batch), ROLE_PROPERTY.get(role, 'P161'))
        payload = _request(query)
        if not isinstance(payload, dict):
            continue
        rows = (payload.get('results') or {}).get('bindings')
        if not isinstance(rows, list):
            logger.info('-> [persondata]: production countries unavailable')
            continue
        found = {personId: {'countries': set(), 'imdb_ids': set()} for personId in batch}
        for row in rows:
            if not isinstance(row, dict):
                continue
            personId = (row.get('tmdb') or {}).get('value')
            if personId not in found:
                continue
            country = (row.get('country') or {}).get('value')
            imdbId = (row.get('imdb') or {}).get('value')
            if country:
                found[personId]['countries'].add(country.upper())
            if imdbId and re.fullmatch(r'tt\d{5,10}', imdbId):
                found[personId]['imdb_ids'].add(imdbId)
        for personId, profile in found.items():
            entry = {key: sorted(value) for key, value in profile.items()}
            entry['ts'] = now
            result[personId] = entry
            cache['profile:' + _cacheKey(role, personId)] = entry
            changed = True
    if changed:
        _saveCache(cache)
    return result


def summarizeImdb(ratings):
    values = [float(rating) for rating in ratings if rating and 0 < float(rating) <= 10]
    if not values:
        return {'imdb_count': 0}
    return {'imdb_best': max(values), 'imdb_average': sum(values) / len(values),
            'imdb_count': len(values)}


def imdbScores(personIds, profiles):
    import xbmc
    import xbmcgui
    from resources.lib import plotinfo
    from concurrent.futures import ThreadPoolExecutor

    imdbIds = sorted({imdbId for personId in personIds
                      for imdbId in (profiles.get(str(personId)) or {}).get('imdb_ids', [])})
    ratings = {}
    cache = _loadCache()
    now = int(time.time())
    for imdbId in imdbIds:
        entry = cache.get('imdb:' + imdbId) or {}
        if now - int(entry.get('ts', 0)) < CACHE_MAX_AGE and 0 < float(entry.get('rating') or 0) <= 10:
            ratings[imdbId] = float(entry['rating'])
    pending = [imdbId for imdbId in imdbIds if imdbId not in ratings]
    dialog = xbmcgui.DialogProgress()
    dialog.create('GerXStream', cConfig().getLocalizedString(31616))
    monitor = xbmc.Monitor()
    executor = ThreadPoolExecutor(max_workers=6)
    changed = False
    try:
        for start in range(0, len(pending), 6):
            if dialog.iscanceled() or monitor.abortRequested():
                return None
            batch = pending[start:start + 6]
            fetched = executor.map(plotinfo.omdbRatings, batch)
            for imdbId, data in zip(batch, fetched):
                ratings[imdbId] = (data.get('imdb') or (0, 0))[0]
                if ratings[imdbId]:
                    cache['imdb:' + imdbId] = {'rating': ratings[imdbId], 'ts': now}
                    changed = True
            dialog.update(min(100, (start + len(batch)) * 100 // max(1, len(pending))))
        return {str(personId): summarizeImdb(ratings.get(imdbId) for imdbId in
                (profiles.get(str(personId)) or {}).get('imdb_ids', [])) for personId in personIds}
    finally:
        executor.shutdown(wait=False)
        dialog.close()
        if changed:
            _saveCache(cache)
