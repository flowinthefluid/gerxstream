# -*- coding: utf-8 -*-
# Python 3
"""Kategorien quer ueber alle Quellen, gespeist aus TMDB.

Die Site-Plugins bieten je nach Webseite nur "Neu" und "Zuletzt hinzugefuegt".
Dieses Modul baut die Kategorien stattdessen aus TMDB auf - Genres, Sammlungen
wie das MCU, Charts, Jahrzehnte und die Filme angesagter Schauspieler - und
uebergibt den gewaehlten Titel an die globale Suche. Damit gilt jede Kategorie
fuer alle aktivierten Quellen gleichzeitig, statt fuer eine einzelne Seite.

Sicherheit: saemtliche Werte, die aus der plugin://-URL kommen, werden gegen
feste Whitelists geprueft, bevor daraus eine TMDB-Abfrage gebaut wird. Es
entsteht nie ein Abfrage-String direkt aus einem URL-Parameter (vgl. S8).
"""

from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.tmdb import cTMDB
from resources.lib.tools import logger

SITE_IDENTIFIER = 'categories'

# Nur diese Ebenen sind ueber die URL erreichbar.
LEVELS = ('root', 'genres', 'collections', 'charts', 'decades', 'people',
          'genreList', 'entries')

MEDIA_TYPES = ('movie', 'tv')

# Sammlungen ueber TMDB-Keywords. IDs gegen /search/keyword geprueft.
COLLECTIONS = (
    ('Marvel Cinematic Universe', 180547),
    ('DC Extended Universe', 229266),
    ('Star Wars', 379196),
    ('Superhelden', 9715),
    ('Zombies', 12377),
    ('Videospielverfilmungen', 41645),
    ('Weihnachten', 207317),
)

# Charts: Kennung -> (TMDB-Pfad ohne Medientyp, zusaetzliche Abfrage)
# 'discover' bedeutet: ueber discover/<typ> mit den angegebenen Parametern.
CHARTS = (
    ('trending', 30818, None, ''),
    ('popular', 30819, 'popular', ''),
    ('top_rated', 30820, 'discover',
     'sort_by=vote_average.desc&vote_count.gte=1000'),
    ('now_playing', 30821, 'now_playing', ''),
    ('upcoming', 30822, 'upcoming', ''),
)

# Serien kennen now_playing/upcoming nicht - dort heissen sie anders.
CHARTS_TV_ALIAS = {'now_playing': 'on_the_air', 'upcoming': 'airing_today'}

DECADES = (2020, 2010, 2000, 1990, 1980, 1970, 1960)

# Genres, die TMDB nur fuer Serien bzw. nur fuer Filme kennt.
TV_ONLY_GENRES = (10759, 10762, 10763, 10764, 10765, 10766, 10767, 10768)
MOVIE_ONLY_GENRES = (12, 14, 28, 35, 36, 37, 53, 80, 878, 10402, 10749, 10752)


def _label(stringId, fallback=''):
    try:
        return cConfig().getLocalizedString(stringId) or fallback
    except Exception:
        return fallback


def _mediaType(params):
    """Medientyp aus der URL, gegen die Whitelist geprueft."""
    value = params.getValue('catMedia')
    return value if value in MEDIA_TYPES else 'movie'


def _int(params, name, default=0):
    """Ganzzahliger URL-Parameter. Alles andere ergibt den Vorgabewert."""
    value = params.getValue(name)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def _addFolder(title, function, params, thumbnail=''):
    oGuiElement = cGuiElement(title, SITE_IDENTIFIER, function)
    if thumbnail:
        oGuiElement.setThumbnail(thumbnail)
    cGui().addFolder(oGuiElement, params)


def showMenu():
    """Einstiegspunkt. Verteilt auf die Ebene aus der URL."""
    params = ParameterHandler()
    level = params.getValue('catLevel')
    if level not in LEVELS:
        level = 'root'
    handler = {
        'root': _root,
        'genres': _mediaChoice,
        'collections': _collections,
        'charts': _charts,
        'decades': _decades,
        'people': _people,
        'genreList': _genreList,
        'entries': _entries,
    }[level]
    handler(params)


def _root(params):
    for level, stringId, fallback in (
            ('genres', 30506, 'Genre'),
            ('collections', 30815, 'Sammlungen'),
            ('charts', 30816, 'Charts'),
            ('decades', 30817, 'Jahrzehnte'),
            ('people', 30823, 'Beliebte Schauspieler')):
        params.setParam('catLevel', level)
        _addFolder(_label(stringId, fallback), 'categories', params)
    cGui().setEndOfDirectory()


def _mediaChoice(params):
    """Filme oder Serien, bevor die Genreliste kommt."""
    for media, stringId, fallback in (('movie', 30502, 'Filme'),
                                      ('tv', 30511, 'Serien')):
        params.setParam('catLevel', 'genreList')
        params.setParam('catMedia', media)
        _addFolder(_label(stringId, fallback), 'categories', params)
    cGui().setEndOfDirectory()


def _genreList(params):
    media = _mediaType(params)
    excluded = TV_ONLY_GENRES if media == 'movie' else MOVIE_ONLY_GENRES
    genres = sorted(((name, gid) for gid, name in cTMDB.TMDB_GENRES.items()
                     if gid not in excluded),
                    key=lambda item: item[0])
    for name, gid in genres:
        params.setParam('catLevel', 'entries')
        params.setParam('catMedia', media)
        params.setParam('catGenre', str(gid))
        params.setParam('catChart', '')
        params.setParam('catKeyword', '')
        params.setParam('catDecade', '')
        params.setParam('catPerson', '')
        params.setParam('page', '1')
        _addFolder(name, 'categories', params)
    cGui().setEndOfDirectory()


def _collections(params):
    for name, keywordId in COLLECTIONS:
        params.setParam('catLevel', 'entries')
        params.setParam('catMedia', 'movie')
        params.setParam('catKeyword', str(keywordId))
        params.setParam('catGenre', '')
        params.setParam('catChart', '')
        params.setParam('catDecade', '')
        params.setParam('catPerson', '')
        params.setParam('page', '1')
        _addFolder(name, 'categories', params)
    cGui().setEndOfDirectory()


def _charts(params):
    for media, mediaString, mediaFallback in (('movie', 30502, 'Filme'),
                                              ('tv', 30511, 'Serien')):
        mediaName = _label(mediaString, mediaFallback)
        for key, stringId, _path, _extra in CHARTS:
            params.setParam('catLevel', 'entries')
            params.setParam('catMedia', media)
            params.setParam('catChart', key)
            params.setParam('catGenre', '')
            params.setParam('catKeyword', '')
            params.setParam('catDecade', '')
            params.setParam('catPerson', '')
            params.setParam('page', '1')
            _addFolder('%s - %s' % (mediaName, _label(stringId, key)),
                       'categories', params)
    cGui().setEndOfDirectory()


def _decades(params):
    for decade in DECADES:
        params.setParam('catLevel', 'entries')
        params.setParam('catMedia', 'movie')
        params.setParam('catDecade', str(decade))
        params.setParam('catGenre', '')
        params.setParam('catChart', '')
        params.setParam('catKeyword', '')
        params.setParam('catPerson', '')
        params.setParam('page', '1')
        _addFolder('%ser' % decade, 'categories', params)
    cGui().setEndOfDirectory()


def _people(params):
    """Angesagte Schauspieler; ein Klick zeigt deren Filme."""
    page = _int(params, 'page', 1)
    data = cTMDB().getUrl('person/popular', page) or {}
    results = data.get('results') or []
    if not results:
        cGui().showInfo()
        return
    for person in results:
        name = person.get('name')
        personId = person.get('id')
        if not name or not personId:
            continue
        thumb = ''
        if person.get('profile_path'):
            thumb = 'https://image.tmdb.org/t/p/w342' + person['profile_path']
        params.setParam('catLevel', 'entries')
        params.setParam('catMedia', 'movie')
        params.setParam('catPerson', str(personId))
        params.setParam('catGenre', '')
        params.setParam('catChart', '')
        params.setParam('catKeyword', '')
        params.setParam('catDecade', '')
        params.setParam('page', '1')
        _addFolder(name, 'categories', params, thumb)
    if data.get('page', 1) < data.get('total_pages', 1):
        params.setParam('catLevel', 'people')
        params.setParam('page', str(page + 1))
        cGui().addNextPage(SITE_IDENTIFIER, 'categories', params)
    cGui().setEndOfDirectory()


def _buildQuery(params):
    """Baut Pfad und Abfrage aus geprueften Werten. Nie direkt aus der URL."""
    media = _mediaType(params)
    page = _int(params, 'page', 1)
    chart = params.getValue('catChart')
    genreId = _int(params, 'catGenre')
    keywordId = _int(params, 'catKeyword')
    decade = _int(params, 'catDecade')
    personId = _int(params, 'catPerson')

    known = dict((key, (path, extra)) for key, _s, path, extra in CHARTS)
    if chart in known:
        path, extra = known[chart]
        if path is None:  # Trending hat einen eigenen Pfad
            return 'trending/%s/week' % media, '', page
        if path != 'discover':
            if media == 'tv':
                path = CHARTS_TV_ALIAS.get(path, path)
            return '%s/%s' % (media, path), '', page
        return 'discover/%s' % media, extra, page

    terms = ['sort_by=popularity.desc']
    if genreId:
        terms.append('with_genres=%s' % genreId)
    if keywordId:
        terms.append('with_keywords=%s' % keywordId)
    if personId:
        terms.append('with_cast=%s' % personId)
    if decade:
        field = 'primary_release_date' if media == 'movie' else 'first_air_date'
        terms.append('%s.gte=%s-01-01' % (field, decade))
        terms.append('%s.lte=%s-12-31' % (field, decade + 9))
    # Ohne Mindeststimmen stehen unveroeffentlichte Eintraege ohne Bewertung
    # ganz oben; bei Sammlungen ist die Menge klein, da stoert es nicht.
    if not keywordId:
        terms.append('vote_count.gte=50')
    return 'discover/%s' % media, '&'.join(terms), page


def _entries(params):
    media = _mediaType(params)
    path, extra, page = _buildQuery(params)
    data = cTMDB().getUrl(path, page, extra) or {}
    results = data.get('results') or []
    if not results:
        logger.info('-> [categories]: keine Treffer fuer %s (%s)' % (path, extra))
        cGui().showInfo()
        return

    total = len(results)
    for item in results:
        # discover/movie liefert 'title', discover/tv 'name'.
        title = item.get('title') or item.get('name')
        if not title:
            continue
        oGuiElement = cGuiElement(title, SITE_IDENTIFIER, 'searchTMDB')
        oGuiElement.setMediaType('movie' if media == 'movie' else 'tvshow')
        released = item.get('release_date') or item.get('first_air_date') or ''
        if len(released) >= 4 and released[:4].isdigit():
            oGuiElement.setYear(released[:4])
        if item.get('overview'):
            oGuiElement.setDescription(item['overview'])
        if item.get('poster_path'):
            oGuiElement.setThumbnail('https://image.tmdb.org/t/p/w342'
                                     + item['poster_path'])
        if item.get('backdrop_path'):
            oGuiElement.setFanart('https://image.tmdb.org/t/p/w1280'
                                  + item['backdrop_path'])
        # Der Klick geht in die globale Suche - so gilt die Kategorie fuer
        # alle aktivierten Quellen, nicht nur fuer eine Webseite.
        params.setParam('searchTitle', title)
        cGui().addFolder(oGuiElement, params, True, total)

    if data.get('page', 1) < data.get('total_pages', 1):
        params.setParam('catLevel', 'entries')
        params.setParam('page', str(page + 1))
        cGui().addNextPage(SITE_IDENTIFIER, 'categories', params)
    cGui().setView('movies' if media == 'movie' else 'tvshows')
    cGui().setEndOfDirectory()
