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
from resources.lib.favorites import favoriteActors
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.tmdb import cTMDB
from resources.lib.tools import logger
from urllib.parse import quote_plus

SITE_IDENTIFIER = 'categories'

# Nur diese Ebenen sind ueber die URL erreichbar.
LEVELS = ('root', 'indexall', 'genres', 'collections', 'charts', 'decades',
          'keywords', 'peopleMenu', 'people', 'genreList', 'entries',
          'ratings', 'outsideHollywood', 'companies', 'locations',
          'mediatheken')

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

# Die People-API wird seitenweise abgefragt. Die Zahl der beliebten
# Regisseure ist deutlich kleiner als die der Schauspieler, weshalb beide
# Grenzen getrennt einstellbar sind.
ACTOR_DEFAULT_LIMIT = 500
DIRECTOR_DEFAULT_LIMIT = 100
PEOPLE_MIN_LIMIT = 25
PEOPLE_MAX_LIMIT = 500
KEYWORD_SEARCH_CACHE = {}

# Vorgefertigte Themenabfragen ueber TMDB-Keywords.
KEYWORDS = (
    ('True Crime', 241495),
    ('Zeitreise', 4379),
    ('Postapokalypse', 4458),
    ('Kuenstliche Intelligenz', 4565),
    ('Gefaengnis', 4202),
    ('Wikinger', 15126),
    ('Mittelalter', 15167),
    ('Spionage', 470),
    ('Kaempfe und Kampfsport', 19096),
    ('Hexen und Magie', 6152),
    ('Cyberpunk', 287501),
    ('Heist / Coup', 10051),
    ('Survival', 9717),
    ('Gericht und Anwaelte', 9672),
    ('Psychothriller', 1710),
    ('Found Footage', 18035),
    ('Roadtrip', 9713),
    ('Musik und Bands', 18016),
    ('Roboter', 14544),
    ('Aliens', 9951),
    ('Vampire', 3133),
    ('Werwoelfe', 18024),
    ('Rache', 9748),
    ('Gefaehrliche Spiele', 1690),
    ('Gefaengnisausbruch', 158091),
    ('Katastrophen', 304),
    ('Familiengeheimnisse', 15440),
    ('Dystopie', 4563),
    ('Noir', 'kw:noir'),
    ('Sport', 'kw:sport'),
    ('Rennen', 'kw:racing'),
    ('Krieg', 'kw:war'),
    ('Uebernatuerliches', 'kw:supernatural'),
    ('Superhelden', 'kw:superhero'),
    ('Antihelden', 'kw:antihero'),
    ('Intrigen', 'kw:intrigue'),
    ('Mafia', 'kw:mafia'),
    ('Historienstoffe', 'kw:period drama'),
    ('Altes Aegypten', 'kw:ancient egypt'),
    ('Samurai', 'kw:samurai'),
    ('Piraten', 'kw:pirate'),
    ('Kaiju', 'kw:kaiju'),
    ('Mecha', 'kw:mecha'),
    ('Space Opera', 'kw:space opera'),
    ('Parallelwelten', 'kw:parallel universe'),
    ('Verschwoerungen', 'kw:conspiracy'),
    ('Biografien', 'kw:biography'),
    ('Militaer', 'kw:military'),
    ('Anwaelte und Justiz', 'kw:courtroom'),
    ('Polizei und Ermittlungen', 'kw:police investigation'),
    ('Gefaengnisausbruch', 'kw:prison escape'),
    ('Sekten und Kulte', 'kw:cult'),
    ('Schatzsuche', 'kw:treasure hunt'),
    ('Insel-Settings', 'kw:island'),
    ('Wuestenabenteuer', 'kw:desert'),
    ('Seefahrt und Ozean', 'kw:ocean'),
    ('Bergwelten', 'kw:mountain'),
    ('Epidemie und Virus', 'kw:pandemic'),
    ('Serienkiller', 'kw:serial killer'),
    ('Entfuehrung', 'kw:kidnapping'),
    ('Verschollene und Vermisste', 'kw:missing person'),
    ('Drogenkartelle', 'kw:drug cartel'),
    ('Gangster und Unterwelt', 'kw:underworld'),
    ('Korruption', 'kw:corruption'),
    ('Politik und Macht', 'kw:politics'),
    ('Koenigshaeuser und Adel', 'kw:royalty'),
    ('Geheimdienst und Agenten', 'kw:secret agent'),
    ('Hacking und Cyberkriminalitaet', 'kw:hacker'),
    ('Journalismus und Medien', 'kw:journalism'),
    ('Aerzte und Krankenhaus', 'kw:hospital'),
    ('Schule und Universitaet', 'kw:school'),
    ('Familie und Erwachsenwerden', 'kw:coming of age'),
    ('Freundschaft', 'kw:friendship'),
    ('Liebe und Romantik', 'kw:romance'),
    ('Musicals', 'kw:musical'),
    ('Tanz', 'kw:dancing'),
    ('Kochen und Essen', 'kw:cooking'),
    ('Natur und Wildnis', 'kw:wilderness'),
    ('Geister', 'kw:ghost'),
    ('Daemonen', 'kw:demon'),
    ('Monster', 'kw:monster'),
    ('Mystery und Ungeklaertes', 'kw:mystery'),
    ('Psychologie und Trauma', 'kw:psychology'),
    ('Traeume und Albtraeume', 'kw:nightmare'),
    ('Paralleluniversen', 'kw:multiverse'),
    ('Weltraumforschung', 'kw:space travel'),
    ('Rettung und Katastrophenschutz', 'kw:rescue'),
    ('Historische Stoffe (keine Zeitreise)', 'kw:historical fiction'),
    ('Antike und Roemisches Reich', 'kw:ancient rome'),
    ('Ritter und Burgen', 'kw:knight'),
    ('Cowboys und Wilder Westen', 'kw:wild west'),
    ('Japanisches Feudalzeitalter', 'kw:feudal japan'),
    ('Mittelalterliche Fantasy', 'kw:medieval fantasy'),
)

RATING_PRESETS = (
    ('IMDb ueber 7.5 (Filme)', 'imdb75_movies'),
    ('IMDb ueber 8.0 (Filme)', 'imdb80_movies'),
    ('IMDb ueber 7.5 (Serien)', 'imdb75_tv'),
    ('IMDb ueber 8.0 (Serien)', 'imdb80_tv'),
)

OUTSIDE_HOLLYWOOD_PRESETS = (
    ('Drehorte ausserhalb USA', 'outside_locations'),
    ('Keine Hollywood Produktion', 'no_hollywood_companies'),
)

COMPANY_PRESETS = (
    ('Miramax', 'company_miramax'),
    ('Lucasfilm', 'company_lucasfilm'),
    ('MGM', 'company_mgm'),
    ('Warner Bros.', 'company_warner'),
    ('Paramount', 'company_paramount'),
    ('Universal Pictures', 'company_universal'),
    ('20th Century Studios', 'company_20th'),
    ('Walt Disney Pictures', 'company_disney'),
    ('Pixar', 'company_pixar'),
    ('DreamWorks', 'company_dreamworks'),
    ('Studio Ghibli', 'company_ghibli'),
    ('A24', 'company_a24'),
    ('Blumhouse', 'company_blumhouse'),
    ('Netflix', 'company_netflix'),
)

LOCATION_PRESETS = (
    ('Deutschland: deutsche Produktionen', 'location_germany_production'),
    # TMDB hat keinen Discover-Filter fuer den physischen Drehort. Das
    # Germany-Keyword ist daher die beste verfuegbare Quersuche fuer Filme,
    # deren Handlung oder Produktionsdaten Deutschland zuordnen.
    ('Deutschland: Schauplatz / Drehorte', 'kw:germany'),
    ('Paris und Frankreich', 'location_france'),
    ('London und UK', 'location_uk'),
    ('Tokio und Japan', 'location_japan'),
    ('Skandinavien', 'location_scandinavia'),
    ('Mittelmeerraum', 'location_mediterranean'),
    ('Suedamerika', 'location_south_america'),
    ('Island und Nordatlantik', 'location_nordatlantic'),
)

# Kuratierte Discover-Abfragen, damit Kategorien schnell bleiben und nicht
# pro Ordnerlauf dynamisch zusammengebaut werden muessen.
PRESET_QUERIES = {
    'imdb75_movies': ('movie', 'sort_by=vote_average.desc&vote_average.gte=7.5&vote_count.gte=800'),
    'imdb80_movies': ('movie', 'sort_by=vote_average.desc&vote_average.gte=8&vote_count.gte=1500'),
    'imdb75_tv': ('tv', 'sort_by=vote_average.desc&vote_average.gte=7.5&vote_count.gte=400'),
    'imdb80_tv': ('tv', 'sort_by=vote_average.desc&vote_average.gte=8&vote_count.gte=700'),
    'outside_locations': ('movie', 'with_origin_country=DE|FR|IT|ES|JP|KR|IN|SE|NO|DK|FI|IS&sort_by=popularity.desc&vote_count.gte=50'),
    'no_hollywood_companies': ('movie', 'without_companies=2|3|4|25|33|174|420|521|6194&sort_by=popularity.desc&vote_count.gte=50'),
    'company_miramax': ('movie', 'with_companies=14&sort_by=popularity.desc&vote_count.gte=50'),
    'company_lucasfilm': ('movie', 'with_companies=1&sort_by=popularity.desc&vote_count.gte=50'),
    'company_mgm': ('movie', 'with_companies=8411&sort_by=popularity.desc&vote_count.gte=50'),
    'company_warner': ('movie', 'with_companies=174&sort_by=popularity.desc&vote_count.gte=50'),
    'company_paramount': ('movie', 'with_companies=4&sort_by=popularity.desc&vote_count.gte=50'),
    'company_universal': ('movie', 'with_companies=33&sort_by=popularity.desc&vote_count.gte=50'),
    'company_20th': ('movie', 'with_companies=25&sort_by=popularity.desc&vote_count.gte=50'),
    'company_disney': ('movie', 'with_companies=2&sort_by=popularity.desc&vote_count.gte=50'),
    'company_pixar': ('movie', 'with_companies=3&sort_by=popularity.desc&vote_count.gte=50'),
    'company_dreamworks': ('movie', 'with_companies=521&sort_by=popularity.desc&vote_count.gte=50'),
    'company_ghibli': ('movie', 'with_companies=10342&sort_by=popularity.desc&vote_count.gte=50'),
    'company_a24': ('movie', 'with_companies=41077&sort_by=popularity.desc&vote_count.gte=50'),
    'company_blumhouse': ('movie', 'with_companies=3172&sort_by=popularity.desc&vote_count.gte=50'),
    'company_netflix': ('movie', 'with_companies=213&sort_by=popularity.desc&vote_count.gte=50'),
    'location_germany_production': ('movie', 'with_origin_country=DE&sort_by=popularity.desc&vote_count.gte=50'),
    'location_france': ('movie', 'with_origin_country=FR&sort_by=popularity.desc&vote_count.gte=50'),
    'location_uk': ('movie', 'with_origin_country=GB&sort_by=popularity.desc&vote_count.gte=50'),
    'location_japan': ('movie', 'with_origin_country=JP&sort_by=popularity.desc&vote_count.gte=50'),
    'location_scandinavia': ('movie', 'with_origin_country=SE|NO|DK|FI|IS&sort_by=popularity.desc&vote_count.gte=50'),
    'location_mediterranean': ('movie', 'with_origin_country=IT|ES|GR|TR|MA|TN&sort_by=popularity.desc&vote_count.gte=50'),
    'location_south_america': ('movie', 'with_origin_country=AR|BR|CL|CO|PE|UY&sort_by=popularity.desc&vote_count.gte=50'),
    'location_nordatlantic': ('movie', 'with_origin_country=IS|NO|FO&sort_by=popularity.desc&vote_count.gte=50'),
}

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
        'indexall': _indexAll,
        'genres': _mediaChoice,
        'collections': _collections,
        'charts': _charts,
        'decades': _decades,
        'keywords': _keywords,
        'peopleMenu': _peopleMenu,
        'people': _people,
        'genreList': _genreList,
        'entries': _entries,
        'ratings': _ratings,
        'outsideHollywood': _outsideHollywood,
        'companies': _companies,
        'locations': _locations,
        'mediatheken': _mediatheken,
    }[level]
    handler(params)


def _root(params):
    params.setParam('catLevel', 'indexall')
    _addFolder(_label(30857, 'Alle'), 'categories', params)
    params.setParam('catLevel', 'mediatheken')
    _addFolder(_label(31500, 'Mediatheken'), 'categories', params)
    for level, stringId, fallback in (
            ('genres', 30506, 'Genre'),
            ('collections', 30815, 'Sammlungen'),
            ('charts', 30816, 'Charts'),
            ('decades', 30817, 'Jahrzehnte'),
            ('keywords', 30859, 'Themen'),
            ('peopleMenu', 30823, 'Beliebte Schauspieler')):
        params.setParam('catLevel', level)
        _addFolder(_label(stringId, fallback), 'categories', params)

    for level, title in (
            ('ratings', 'Bewertungen (IMDb/Top Rated)'),
            ('outsideHollywood', 'Ausserhalb Hollywood'),
            ('companies', 'Produktionsfirmen'),
            ('locations', 'Beruehmte Drehorte')):
        params.setParam('catLevel', level)
        _addFolder(title, 'categories', params)
    cGui().setEndOfDirectory()


# Eigene Mediathek-Quellen; die Sender-Mediatheken darunter laufen ueber die
# Senderfilter von MediathekViewWeb (ARD, ZDF, 3sat, ORF, SRF, Dritte ...).
MEDIATHEK_SITES = ('ardmediathek', 'arte', 'mediathekviewweb')


def _mediathekChannels():
    try:
        import os
        import sys
        sitesDir = os.path.join(cConfig().getAddonInfo('path'), 'sites')
        if sitesDir not in sys.path:
            sys.path.append(sitesDir)
        return tuple(__import__('mediathekviewweb').CHANNELS)
    except Exception as e:
        logger.error('-> [categories]: MediathekViewWeb-Senderliste nicht ladbar (%s)' % type(e).__name__)
        return ()


def _mediatheken(params):
    """Alle Mediatheken des deutschen und oesterreichischen Fernsehens."""
    from resources.lib.handler.pluginHandler import cPluginHandler
    enabled = dict((plugin.get('id'), plugin) for plugin in cPluginHandler().getAvailablePlugins())
    listed = 0
    for siteId in MEDIATHEK_SITES:
        plugin = enabled.get(siteId)
        if not plugin:
            continue
        element = cGuiElement(plugin.get('name') or siteId, siteId, 'load')
        if plugin.get('icon'):
            element.setThumbnail(plugin['icon'])
        cGui().addFolder(element)
        listed += 1
    if 'mediathekviewweb' in enabled:
        for label, channel in _mediathekChannels():
            channelParams = ParameterHandler()
            channelParams.setParam('mvwMode', 'channel')
            channelParams.setParam('mvwValue', channel)
            channelParams.setParam('page', '0')
            element = cGuiElement(_label(31501, '%s-Mediathek').replace('%s', label),
                                  'mediathekviewweb', 'showEntries')
            cGui().addFolder(element, channelParams)
            listed += 1
    if not listed:
        cGui().showInfo('GerXStream', _label(31502, 'Keine Mediathek-Quelle aktiviert'))
    cGui().setEndOfDirectory()


def _indexAll(params):
    """Kombinierter Index aus Trend-Filmen und -Serien, quelluebergreifend."""
    page = _int(params, 'page', 1)
    movie = cTMDB().getUrl('trending/movie/week', page) or {}
    tv = cTMDB().getUrl('trending/tv/week', page) or {}
    items = (movie.get('results') or []) + (tv.get('results') or [])
    if not items:
        cGui().showInfo()
        return

    seen = set()
    total = len(items)
    for item in items:
        title = item.get('title') or item.get('name')
        if not title:
            continue
        year = (item.get('release_date') or item.get('first_air_date') or '')[:4]
        key = (title.lower(), year)
        if key in seen:
            continue
        seen.add(key)

        oGuiElement = cGuiElement(title, SITE_IDENTIFIER, 'searchTMDB')
        if year.isdigit():
            oGuiElement.setYear(year)
        if item.get('overview'):
            oGuiElement.setDescription(item['overview'])
        if item.get('poster_path'):
            oGuiElement.setThumbnail('https://image.tmdb.org/t/p/w342' + item['poster_path'])
        if item.get('backdrop_path'):
            oGuiElement.setFanart('https://image.tmdb.org/t/p/w1280' + item['backdrop_path'])
        params.setParam('searchTitle', title)
        params.setParam('searchOriginalTitle', item.get('original_title') or item.get('original_name') or '')
        params.setParam('searchYear', year)
        params.setParam('searchMedia', 'movie' if item.get('title') else 'tvshow')
        params.setParam('searchTmdbID', item.get('id'))
        cGui().addFolder(oGuiElement, params, True, total)

    if page < max(movie.get('total_pages', 1), tv.get('total_pages', 1)):
        params.setParam('catLevel', 'indexall')
        params.setParam('page', str(page + 1))
        cGui().addNextPage(SITE_IDENTIFIER, 'categories', params)
    cGui().setView('movies')
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
        params.setParam('catPreset', '')
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
        params.setParam('catPreset', '')
        params.setParam('page', '1')
        _addFolder(name, 'categories', params)
    cGui().setEndOfDirectory()


def _keywords(params):
    for name, keywordRef in KEYWORDS:
        params.setParam('catLevel', 'entries')
        if isinstance(keywordRef, int):
            params.setParam('catMedia', 'movie')
            params.setParam('catKeyword', str(keywordRef))
            params.setParam('catPreset', '')
        else:
            params.setParam('catMedia', '')
            params.setParam('catKeyword', '')
            params.setParam('catPreset', str(keywordRef))
        params.setParam('catGenre', '')
        params.setParam('catChart', '')
        params.setParam('catDecade', '')
        params.setParam('catPerson', '')
        params.setParam('page', '1')
        _addFolder(name, 'categories', params)
    cGui().setEndOfDirectory()


def _keywordIdByTerm(term):
    key = (term or '').strip().lower()
    if not key:
        return 0
    if key in KEYWORD_SEARCH_CACHE:
        return KEYWORD_SEARCH_CACHE[key]

    data = cTMDB().getUrl('search/keyword', 1, 'query=%s' % quote_plus(term)) or {}
    results = data.get('results') or []

    exactId = 0
    firstId = 0
    for entry in results:
        if not isinstance(entry, dict):
            continue
        candidate = entry.get('id')
        if not candidate:
            continue
        if not firstId:
            firstId = candidate
        if (entry.get('name') or '').strip().lower() == key:
            exactId = candidate
            break

    resolved = exactId or firstId or 0
    KEYWORD_SEARCH_CACHE[key] = resolved
    return resolved


def _addPresetFolders(params, entries):
    for title, presetKey in entries:
        params.setParam('catLevel', 'entries')
        params.setParam('catMedia', '')
        params.setParam('catPreset', presetKey)
        params.setParam('catGenre', '')
        params.setParam('catChart', '')
        params.setParam('catKeyword', '')
        params.setParam('catDecade', '')
        params.setParam('catPerson', '')
        params.setParam('page', '1')
        _addFolder(title, 'categories', params)


def _ratings(params):
    _addPresetFolders(params, RATING_PRESETS)
    cGui().setEndOfDirectory()


def _outsideHollywood(params):
    _addPresetFolders(params, OUTSIDE_HOLLYWOOD_PRESETS)
    cGui().setEndOfDirectory()


def _companies(params):
    _addPresetFolders(params, COMPANY_PRESETS)
    cGui().setEndOfDirectory()


def _locations(params):
    _addPresetFolders(params, LOCATION_PRESETS)
    cGui().setEndOfDirectory()


def _peopleMenu(params):
    actorLimit = _peopleLimit('Acting')
    directorLimit = _peopleLimit('Directing')
    ownActors = len(favoriteActors())
    actorTitle = _label(30823, 'Beliebte Schauspieler') + ' (%s' % (actorLimit or _label(31602, 'Alle'))
    if ownActors:
        actorTitle += ' + %s eigene' % ownActors
    actorTitle += ')'
    for title, role in ((actorTitle, 'Acting'),
                        (_label(30860, 'Beliebte Regisseure') + ' (%s)' % (directorLimit or _label(31602, 'Alle')), 'Directing')):
        params.setParam('catLevel', 'people')
        params.setParam('catRole', role)
        _addFolder(title, 'categories', params)
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
            params.setParam('catPreset', '')
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
        params.setParam('catPreset', '')
        params.setParam('page', '1')
        _addFolder('%ser' % decade, 'categories', params)
    cGui().setEndOfDirectory()


def _addPersonFolder(params, person, title=None):
    """Fuegt eine Person mit einem sicheren TMDB-Cast-Filter hinzu."""
    name = title or person.get('name')
    personId = person.get('id')
    if not name or not personId:
        return False
    thumb = cTMDB().imageUrl(person.get('profile_path'))
    params.setParam('catLevel', 'entries')
    params.setParam('catMedia', 'movie')
    params.setParam('catPerson', str(personId))
    params.setParam('catGenre', '')
    params.setParam('catChart', '')
    params.setParam('catKeyword', '')
    params.setParam('catDecade', '')
    params.setParam('catPreset', '')
    params.setParam('page', '1')
    _addFolder(name, 'categories', params, thumb)
    return True


def _findPersonByName(name):
    """Loest einen eigenen Listeneintrag auf eine TMDB-Person auf."""
    data = cTMDB().getUrl('search/person', 1, 'query=%s' % quote_plus(name)) or {}
    for person in data.get('results') or []:
        if (person.get('name') or '').casefold() == name.casefold() and person.get('id'):
            return person
    for person in data.get('results') or []:
        if person.get('id'):
            return person
    return {}


def _peopleLimit(role):
    setting = 'directorPeopleLimit' if role == 'Directing' else 'actorPeopleLimit'
    default = DIRECTOR_DEFAULT_LIMIT if role == 'Directing' else ACTOR_DEFAULT_LIMIT
    return max(0, min(
        PEOPLE_MAX_LIMIT,
        cConfig().getSettingInt(setting, default)))


def _knownForRating(person):
    """Beste belastbare TMDB-Wertung aus den bekannten Werken einer Person."""
    best = (0.0, 0)
    for item in person.get('known_for') or []:
        try:
            rating = float(item.get('vote_average') or 0)
            votes = int(item.get('vote_count') or 0)
        except (TypeError, ValueError):
            continue
        # Eine 10/10-Wertung aus wenigen Stimmen ist kein brauchbares
        # Popularitaetssignal. 200 Stimmen lassen grosse Ausreisser weg.
        if votes >= 200 and (rating, votes) > best:
            best = (rating, votes)
    return best


PEOPLE_SORT_MODES = ('popularity', 'name', 'rating', 'films', 'awards', 'imdb_best', 'imdb_average')
PEOPLE_GROUPS = (('all', 31602), ('hollywood', 31603), ('german', 31604),
                 ('japanese', 31605), ('korean', 31606), ('indian', 31607), ('other', 31608))


def _peopleGroups(role):
    prefix = 'director' if role == 'Directing' else 'actor'
    valid = {key for key, _labelId in PEOPLE_GROUPS}
    selected = set(cConfig().getSetting(prefix + 'PeopleGroups', 'all').split(',')) & valid
    return selected or {'all'}


def editPeopleGroups(params):
    import xbmcgui

    role = params.getValue('catRole')
    prefix = 'director' if role == 'Directing' else 'actor'
    current = _peopleGroups(role)
    selected = xbmcgui.Dialog().multiselect(
        _label(31601), [_label(labelId) for _key, labelId in PEOPLE_GROUPS],
        preselect=[index for index, (key, _labelId) in enumerate(PEOPLE_GROUPS) if key in current])
    if selected is None:
        return
    groups = [PEOPLE_GROUPS[index][0] for index in selected if 0 <= index < len(PEOPLE_GROUPS)]
    if not groups or groups == ['all']:
        groups = ['all']
    elif len(groups) > 1 and 'all' in groups:
        groups.remove('all')
    cConfig().setSetting(prefix + 'PeopleGroups', ','.join(groups))
    cGui().showInfo('GerXStream', ', '.join(_label(labelId) for key, labelId in PEOPLE_GROUPS
                                          if key in groups), 4)


def _personInGroups(person, groups, profiles):
    if 'all' in groups:
        return True
    from resources.lib import persondata
    profile = profiles.get(str(person.get('id'))) or {}
    return bool(groups & persondata.productionGroups(profile.get('countries') or []))


def _personSortKey(person, sortMode, extra=None):
    name = (person.get('name') or '').casefold()
    popularity = -float(person.get('popularity') or 0)
    if sortMode == 'name':
        return (name,)
    if sortMode == 'rating':
        rating, votes = _knownForRating(person)
        return (-rating, -votes, popularity, name)
    if sortMode in ('imdb_best', 'imdb_average'):
        data = (extra or {}).get(str(person.get('id'))) or {}
        return (-float(data.get(sortMode) or 0), popularity, name)
    if sortMode in ('films', 'awards'):
        data = (extra or {}).get(str(person.get('id'))) or {}
        films = int(data.get('films') or 0)
        awards = int(data.get('oscars') or 0) + int(data.get('grammys') or 0)
        if sortMode == 'films':
            return (-films, -awards, popularity, name)
        return (-awards, -int(data.get('oscars') or 0), -films, popularity, name)
    return (popularity, name)


def _personLabel(person, sortMode, extra):
    """Zeigt bei Film-/Preis-Sortierung die Zahl, nach der sortiert wurde."""
    name = person.get('name') or ''
    data = (extra or {}).get(str(person.get('id')))
    if sortMode in ('imdb_best', 'imdb_average'):
        rating = (data or {}).get(sortMode)
        return '%s  [I]IMDb %.2f[/I]' % (name, rating) if rating else name
    if not data or sortMode not in ('films', 'awards'):
        return name
    details = []
    if sortMode == 'films' and data.get('films'):
        details.append(cConfig().getLocalizedString(31453) % data['films'])
    if data.get('oscars'):
        details.append(cConfig().getLocalizedString(31454) % data['oscars'])
    if data.get('grammys'):
        details.append(cConfig().getLocalizedString(31455) % data['grammys'])
    return '%s  [I]%s[/I]' % (name, ' · '.join(details)) if details else name


def _people(params):
    """TMDB-Popular-Liste nach Rolle, erweitert um eigene Schauspieler."""
    role = 'Directing' if params.getValue('catRole') == 'Directing' else 'Acting'
    peopleLimit = _peopleLimit(role)
    prefix = 'director' if role == 'Directing' else 'actor'
    sortMode = cConfig().getSetting(prefix + 'PeopleSort') or cConfig().getSetting('peopleSort', 'popularity')
    if sortMode not in PEOPLE_SORT_MODES:
        sortMode = 'popularity'
    groups = _peopleGroups(role)
    if sortMode in ('imdb_best', 'imdb_average'):
        from resources.lib import plotinfo
        import xbmcgui
        if not (cConfig().getSetting(plotinfo.OMDB_KEY_SETTING) or '').strip():
            xbmcgui.Dialog().ok('GerXStream', _label(31613))
            cGui().setEndOfDirectory(False)
            return
    page = 1
    listed = 0
    popularListed = 0
    total_pages = 1
    listedIds = set()
    people = []
    targetPool = (peopleLimit if sortMode == 'popularity' and groups == {'all'} and peopleLimit
                  else PEOPLE_MAX_LIMIT)

    # Eigene Namen stehen in der gleichen Schauspielerliste, nicht in einem
    # separaten Unterordner. So erscheint ein im Infofenster gespeicherter
    # Darsteller beim naechsten Oeffnen direkt an erster Stelle.
    if role == 'Acting':
        for name in favoriteActors():
            person = _findPersonByName(name)
            if not person or person.get('id') in listedIds:
                continue
            listedIds.add(person.get('id'))
            people.append(person)

    while popularListed < targetPool and page <= min(total_pages, 500):
        data = cTMDB().getUrl('person/popular', page) or {}
        results = data.get('results') or []
        total_pages = data.get('total_pages', 1)
        if not results:
            break
        for person in results:
            if popularListed >= targetPool:
                break
            if role and person.get('known_for_department') and person.get('known_for_department') != role:
                continue
            personId = person.get('id')
            if not personId or personId in listedIds:
                continue
            listedIds.add(personId)
            people.append(person)
            popularListed += 1
        page += 1

    extra = {}
    profiles = {}
    if 'all' not in groups or sortMode in ('imdb_best', 'imdb_average'):
        from resources.lib import persondata
        profiles = persondata.filmProfiles([person.get('id') for person in people], role)
        if not profiles:
            cGui().showInfo('GerXStream', _label(31614), 4)
            cGui().setEndOfDirectory(False)
            return
    people = [person for person in people if _personInGroups(person, groups, profiles)]
    if sortMode in ('imdb_best', 'imdb_average'):
        from resources.lib import persondata
        extra = persondata.imdbScores([person.get('id') for person in people], profiles)
        if extra is None:
            cGui().setEndOfDirectory(False)
            return
        if not any(data.get('imdb_count') for data in extra.values()):
            cGui().showInfo('GerXStream', _label(31615), 4)
            cGui().setEndOfDirectory(False)
            return
    if sortMode in ('films', 'awards') and people:
        try:
            from resources.lib import persondata
            extra = persondata.counts([person.get('id') for person in people], role)
        except Exception as e:
            logger.error('-> [categories]: person counts unavailable (%s)' % type(e).__name__)
        if not extra:
            cGui().showInfo('GerXStream', cConfig().getLocalizedString(31456), 4)
    ordered = sorted(people, key=lambda item: _personSortKey(item, sortMode, extra))
    if peopleLimit:
        ordered = ordered[:peopleLimit]
    for person in ordered:
        if _addPersonFolder(params, person, _personLabel(person, sortMode, extra)):
            listed += 1

    if listed == 0:
        cGui().showInfo()
        cGui().setEndOfDirectory(False)
        return

    if page <= total_pages and popularListed >= peopleLimit:
        logger.info('-> [categories]: People list capped at %s entries (%s, %s)' %
                    (peopleLimit, role, sortMode))
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
    # ParameterHandler liefert False, wenn der optionale Parameter in einem
    # alten oder manuell erzeugten Kodi-Link fehlt. startswith() auf diesem
    # bool war die Ursache fuer den Absturz bei Schauspielern, Charts und
    # Jahrzehnten.
    presetKey = params.getValue('catPreset') or ''

    if presetKey.startswith('kw:'):
        keywordId = _keywordIdByTerm(presetKey[3:])
        if keywordId:
            return 'discover/%s' % media, 'with_keywords=%s&sort_by=popularity.desc&vote_count.gte=50' % keywordId, page
        logger.info('-> [categories]: kein TMDB-Keyword fuer %r gefunden' % presetKey)
        return 'discover/%s' % media, 'sort_by=popularity.desc&vote_count.gte=50', page

    if presetKey in PRESET_QUERIES:
        media, extra = PRESET_QUERIES[presetKey]
        return 'discover/%s' % media, extra, page

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
        field = 'with_crew' if params.getValue('catRole') == 'Directing' else 'with_cast'
        terms.append('%s=%s' % (field, personId))
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
        params.setParam('searchOriginalTitle', item.get('original_title') or item.get('original_name') or '')
        params.setParam('searchYear', released[:4])
        params.setParam('searchMedia', 'movie' if media == 'movie' else 'tvshow')
        params.setParam('searchTmdbID', item.get('id'))
        cGui().addFolder(oGuiElement, params, True, total)

    if data.get('page', 1) < data.get('total_pages', 1):
        params.setParam('catLevel', 'entries')
        params.setParam('page', str(page + 1))
        cGui().addNextPage(SITE_IDENTIFIER, 'categories', params)
    cGui().setView('movies' if media == 'movie' else 'tvshows')
    cGui().setEndOfDirectory()
