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
