import random
from datetime import date, timedelta
from urllib.parse import parse_qs

import xbmc
import xbmcgui

from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tmdb import cTMDB


def _genres():
    from resources.lib.categories import TV_ONLY_GENRES

    return sorted(((genre_id, name) for genre_id, name in cTMDB.TMDB_GENRES.items()
                   if genre_id not in TV_ONLY_GENRES), key=lambda entry: entry[1])


def _companies():
    from resources.lib.categories import COMPANY_PRESETS, PRESET_QUERIES

    return [(parse_qs(PRESET_QUERIES[key][1])['with_companies'][0], name)
            for name, key in COMPANY_PRESETS]


def _excludedGenres():
    valid = {str(genre_id) for genre_id, name in _genres()}
    return set(cConfig().getSetting('randomExcludedGenres', '').split(',')) & valid


def editGenres():
    genres = _genres()
    excluded = _excludedGenres()
    selected = xbmcgui.Dialog().multiselect(
        cConfig().getLocalizedString(31701), [name for genre_id, name in genres],
        preselect=[index for index, (genre_id, name) in enumerate(genres) if str(genre_id) not in excluded])
    if selected is not None:
        allowed = set(selected)
        cConfig().setSetting('randomExcludedGenres', ','.join(
            str(genre_id) for index, (genre_id, name) in enumerate(genres) if index not in allowed))


def _folder(title, level, mode='', value=''):
    params = ParameterHandler()
    params.setParam('randomLevel', level)
    params.setParam('randomMode', mode)
    params.setParam('randomValue', value)
    cGui().addFolder(cGuiElement(title, 'random', 'randomMovies'), params)


def showMenu():
    params = ParameterHandler()
    level = params.getValue('randomLevel') or 'root'
    if level == 'entries':
        _entries(params)
        return
    if level == 'genres':
        for genre_id, name in _genres():
            _folder(name, 'entries', 'genre', str(genre_id))
    elif level == 'companies':
        for company_id, name in _companies():
            _folder(name, 'entries', 'company', company_id)
    else:
        _folder('Random', 'entries', 'random')
        _folder(cConfig().getLocalizedString(31702), 'genres')
        _folder(cConfig().getLocalizedString(31703), 'companies')
    cGui().setEndOfDirectory()


def _query(mode, value):
    terms = ['include_adult=false', 'sort_by=primary_release_date.asc']
    if mode == 'genre':
        if value not in {str(genre_id) for genre_id, name in _genres()}:
            return None
        terms.append('with_genres=' + value)
    elif mode == 'company':
        if value not in {company_id for company_id, name in _companies()}:
            return None
        terms.append('with_companies=' + value)
    elif mode == 'random':
        excluded = _excludedGenres()
        if len(excluded) == len(_genres()):
            return None
        if excluded:
            terms.append('without_genres=' + ','.join(sorted(excluded)))
    else:
        return None
    return '&'.join(terms)


def sampleCatalog(tmdb, extra, count, canceled=lambda: False, start=None, end=None, progress=lambda count: None):
    start = start or date(1800, 1, 1)
    end = end or date.today()
    selected = []

    def query(first, last, page=1):
        if canceled():
            return {}
        progress(len(selected))
        terms = '%s&primary_release_date.gte=%s&primary_release_date.lte=%s' % (extra, first, last)
        data = tmdb.getUrl('discover/movie', page, terms) or {}
        if canceled():
            return {}
        if 'total_results' not in data:
            raise ValueError(cConfig().getLocalizedString(31715))
        return data

    def collect(first, last, ranks, data):
        if not ranks or canceled():
            return
        total = int(data.get('total_results') or 0)
        if total > 10000:
            if first >= last:
                raise ValueError('TMDB-Seitenlimit fuer einen einzelnen Erscheinungstag erreicht')
            middle = first + timedelta(days=(last - first).days // 2)
            left = query(first, middle)
            if canceled():
                return
            left_count = int(left.get('total_results') or 0)
            collect(first, middle, [rank for rank in ranks if rank < left_count], left)
            right_ranks = [rank - left_count for rank in ranks if rank >= left_count]
            if right_ranks:
                collect(middle + timedelta(days=1), last, right_ranks, query(middle + timedelta(days=1), last))
            return
        pages = {}
        for rank in ranks:
            if rank < total:
                pages.setdefault(rank // 20 + 1, []).append(rank % 20)
        for page, offsets in pages.items():
            if canceled():
                return
            results = (data if page == 1 else query(first, last, page)).get('results') or []
            selected.extend(results[offset] for offset in offsets if offset < len(results))
            progress(len(selected))

    data = query(start, end)
    total = int(data.get('total_results') or 0)
    ranks = random.sample(range(total), min(count, total))
    collect(start, end, ranks, data)
    unique = {item['id']: item for item in selected if item.get('id') and item.get('title')}
    selected = list(unique.values())
    random.shuffle(selected)
    return selected


def _entries(params):
    from resources.lib import plotinfo

    mode = params.getValue('randomMode') or 'random'
    extra = _query(mode, str(params.getValue('randomValue') or ''))
    gui = cGui()
    minimum = plotinfo.minimumRating('randomMinImdb')
    if extra is None:
        gui.showInfo('GerXStream', cConfig().getLocalizedString(31721))
        gui.setEndOfDirectory(False)
        return
    if not plotinfo.requireImdbKey(minimum):
        gui.setEndOfDirectory(False)
        return
    limit = max(1, min(cConfig().getSettingInt('randomItemsCount', 250), 1000))
    progress = xbmcgui.DialogProgress()
    progress.create(cConfig().getLocalizedString(30868))
    monitor = xbmc.Monitor()
    canceled = lambda: progress.iscanceled() or monitor.abortRequested()
    candidate_count = min(limit * 4, 1000) if minimum else limit
    try:
        with cRequestHandler.backgroundRequests():
            pool = sampleCatalog(cTMDB(), extra, candidate_count, canceled,
                                 progress=lambda count: progress.update(min(80, count * 80 // candidate_count)))
            selected = []
            excluded = _excludedGenres() if mode == 'random' else set()
            for index, item in enumerate(pool):
                if canceled():
                    break
                progress.update(80 + int(20 * index / max(len(pool), 1)))
                if excluded & {str(genre_id) for genre_id in item.get('genre_ids') or []}:
                    continue
                if plotinfo.matchesMinimum(item, 'movie', minimum):
                    selected.append(item)
                if len(selected) >= limit:
                    break
            aborted = canceled()
    except ValueError as error:
        gui.showInfo('GerXStream', str(error))
        gui.setEndOfDirectory(False)
        return
    finally:
        progress.close()
    if aborted:
        gui.setEndOfDirectory(False)
        return
    if len(selected) < limit:
        gui.showInfo('GerXStream', cConfig().getLocalizedString(31704) % (len(selected), limit))
    for item in selected:
        element = cGuiElement(item['title'], 'random', 'searchTMDB')
        element.setMediaType('movie')
        year = (item.get('release_date') or '')[:4]
        if year.isdigit():
            element.setYear(year)
        element.setDescription(item.get('overview') or '')
        if item.get('poster_path'):
            element.setThumbnail('https://image.tmdb.org/t/p/w342' + item['poster_path'])
        if item.get('backdrop_path'):
            element.setFanart('https://image.tmdb.org/t/p/w1280' + item['backdrop_path'])
        search = ParameterHandler()
        for key, value in (('searchTitle', item['title']), ('searchOriginalTitle', item.get('original_title') or ''),
                           ('searchYear', year), ('searchMedia', 'movie'), ('searchTmdbID', item['id'])):
            search.setParam(key, value)
        gui.addFolder(element, search, True, len(selected))
    gui.setView('movies')
    gui.setEndOfDirectory()