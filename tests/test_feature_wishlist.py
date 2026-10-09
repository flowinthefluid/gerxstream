# -*- coding: utf-8 -*-
"""Historie-Limit, Browser-Cookie-Import, Personen-Sortierung, Plot-Zusatzinfos."""

import time

from conftest import set_setting
from resources.lib import history, persondata, plotinfo
from resources.lib.handler import protection


# --- Historie -------------------------------------------------------------

def _fill(count):
    history.clear()
    stored = [{'title': 'T%d' % i, 'search_title': 'T%d' % i, 'watched_at': 1000 + i}
              for i in range(count)]
    history._save(stored)


def test_history_limit_up_to_1000():
    _fill(1200)
    set_setting(history.HISTORY_LIMIT_SETTING, '1000')
    assert len(history.entries()) == 1000
    set_setting(history.HISTORY_LIMIT_SETTING, '50')
    assert len(history.entries()) == 50


def test_history_unlimited_keeps_everything():
    _fill(1200)
    set_setting(history.HISTORY_LIMIT_SETTING, '0')
    assert len(history.entries()) == 1200
    assert history.record('Neu')
    assert len(history.entries()) == 1201
    assert history.entries()[0]['title'] == 'Neu'


def test_history_limited_storage_keeps_at_least_1000():
    _fill(1200)
    set_setting(history.HISTORY_LIMIT_SETTING, '10')
    assert history.record('Neu')
    assert len(history._stored()) == history.MAX_LIMIT
    history.clear()


def test_watchlist_series_groups_episodes_and_remembers_latest_provider(monkeypatch, tmp_path):
    from resources.lib import epicfavorites
    monkeypatch.setattr(epicfavorites, '_profilePath', lambda: str(tmp_path / 'favorites.json'))
    monkeypatch.setattr(history, '_historyPath', lambda: str(tmp_path / 'history.json'))
    for index, source in enumerate(('serienstream', 'aniworld', 'serienstream'), 1):
        folder = 'plugin://plugin.video.gerxstream/?site=%s&function=showEpisodes&sUrl=carrie' % source
        assert history.record('CarrieS01E0%d' % index, mediaType='episode', source=source,
                              season='1', episode=str(index), showTitle='Carrie',
                              seriesTitle='Carrie (2026)', year='2026', seriesTarget=folder,
                              target=folder + '&playMode=play&episodeQueue=' + 'a' * 32)
    entries = epicfavorites.watchEntries('watching')
    assert len(entries) == 1
    assert entries[0]['title'] == 'Carrie (2026)'
    assert entries[0]['source'] == 'serienstream'
    assert entries[0]['is_folder'] is True
    assert 'episodeQueue' not in entries[0]['target']
    assert len(history.entries()) == 3


def test_watchlist_preserves_favorite_folders_and_manual_status(monkeypatch, tmp_path):
    from resources.lib import epicfavorites
    monkeypatch.setattr(epicfavorites, '_profilePath', lambda: str(tmp_path / 'favorites.json'))
    assert epicfavorites.importData({'version': 1, 'folders': [], 'entries': []})
    assert epicfavorites.createFolder('', 'Meine Serien')
    entry = {'title': 'Carrie (2026)', 'media_type': 'tvshow', 'is_folder': True,
             'target': 'plugin://plugin.video.gerxstream/?site=serienstream&function=showSeasons'}
    assert epicfavorites.setStatus(entry, 'completed')
    assert epicfavorites.setStatus(entry, 'watching', automatic=True)
    assert len(epicfavorites.watchEntries('completed')) == 1
    exported = epicfavorites.exportData()
    assert exported['folders'][0]['name'] == 'Meine Serien'
    assert exported['watchlist'][0]['title'] == 'Carrie (2026)'


def test_episode_playback_context_retains_series_folder(monkeypatch):
    from resources.lib import playbackstate
    from resources.lib.handler.ParameterHandler import ParameterHandler
    import xbmcgui
    import json

    params = ParameterHandler()
    folder = 'plugin://plugin.video.gerxstream/?site=serienstream&function=showEpisodes&sUrl=carrie'
    params.addParams({'site': 'serienstream', 'mediaType': 'episode', 'season': '1', 'episode': '2',
                      'watchlistTarget': folder, 'watchlistTitle': 'Carrie', 'watchlistYear': '2026'})
    playbackstate.beginPlayback({'title': 'S01E02', 'showTitle': 'Carrie',
                                 'link': 'https://example.test/stream'}, params)
    context = json.loads(xbmcgui.Window(10000).getProperty(playbackstate.PLAYBACK_PROPERTY))
    assert context['history']['seriesTarget'] == folder
    assert context['history']['seriesTitle'] == 'Carrie'
    assert context['history']['year'] == '2026'
    xbmcgui.Window(10000).clearProperty(playbackstate.PLAYBACK_PROPERTY)


def test_watchlist_menu_and_history_timestamp_toggle(monkeypatch, real_strings):
    import sys
    import xml.etree.ElementTree as ET
    from pathlib import Path
    from resources.lib.gui.gui import cGui
    from resources.lib.handler.ParameterHandler import ParameterHandler

    main = _main_module(monkeypatch)
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.gerxstream/', '1', ''])
    added = []
    monkeypatch.setattr(cGui, 'addFolder', lambda self, element, *args: added.append(element))
    monkeypatch.setattr(cGui, 'setView', lambda *args: None)
    monkeypatch.setattr(cGui, 'setEndOfDirectory', lambda *args: None)
    main.showEpicFavorites(ParameterHandler())
    assert [element.getTitle() for element in added] == [
        'Favorites', 'Geplant', 'Am Schauen', 'Abgeschlossen', 'Abgebrochen', 'Historie']
    target = 'plugin://plugin.video.gerxstream/?site=serienstream&function=showSeasons&sUrl=carrie'
    monkeypatch.setattr(history, 'entries', lambda: [{'title': 'CarrieS01E01', 'source': 'serienstream',
                                                     'watched_at': 1700000000, 'series_target': target}])
    for enabled in ('false', 'true'):
        added.clear()
        set_setting('watchHistoryTimestamps', enabled)
        main.showWatchHistory()
        description = added[0].getDescription()
        assert (main._historyTimestamp(1700000000) in description) == (enabled == 'true')
        assert added[0].getItemProperties()['GerXStream.Target'] == target
    settings = ET.parse(Path(__file__).resolve().parents[1] / 'resources' / 'settings.xml')
    assert settings.find(".//setting[@id='watchHistoryTimestamps']/default").text == 'False'


def test_series_folder_context_survives_reopening_and_episode_navigation(monkeypatch, tmp_path):
    import sys
    import xbmcplugin
    from urllib.parse import parse_qsl, urlsplit
    from resources.lib import epicfavorites
    from resources.lib.gui.gui import cGui
    from resources.lib.gui.guiElement import cGuiElement
    from resources.lib.handler.ParameterHandler import ParameterHandler

    monkeypatch.setattr(epicfavorites, '_profilePath', lambda: str(tmp_path / 'favorites.json'))
    monkeypatch.setattr(history, '_historyPath', lambda: str(tmp_path / 'history.json'))
    monkeypatch.setattr(cGui, '_cGui__createContextMenu', lambda self, element, item, *args: item)
    monkeypatch.setattr(cGui, '_episodeQueues', {})
    listed = []
    monkeypatch.setattr(xbmcplugin, 'addDirectoryItem', lambda *args: listed.append(args))
    base = 'plugin://plugin.video.gerxstream/'
    monkeypatch.setattr(sys, 'argv', [base, '1', '?site=serienstream&function=showSearch&sUrl=search'])
    series = cGuiElement('Carrie (2026)', 'serienstream', 'showSeasons')
    series.setMediaType('tvshow')
    params = ParameterHandler()
    params.setParam('sUrl', 'serie/carrie?a=one&b=two')
    params.setParam('TVShowTitle', 'Carrie')
    cGui().addFolder(series, params)
    original = dict(parse_qsl(urlsplit(listed[-1][1]).query))
    folder = original['watchlistTarget']
    for folderOnly in (False, True):
        if folderOnly:
            entry = epicfavorites.watchEntries('watching')[0]
            seriesUrl = epicfavorites.targetForEntry(entry)
        else:
            seriesUrl = listed[-1][1]
        monkeypatch.setattr(sys, 'argv', [base, '1', '?' + urlsplit(seriesUrl).query])
        season = cGuiElement('Staffel 1', 'serienstream', 'showEpisodes')
        season.setMediaType('season')
        params = ParameterHandler()
        params.setParam('sUrl', 'serie/carrie/staffel-1')
        cGui().addFolder(season, params)
        monkeypatch.setattr(sys, 'argv', [base, '1', '?' + urlsplit(listed[-1][1]).query])
        episode = cGuiElement('Folge 2', 'serienstream', 'getHosters')
        episode.setMediaType('episode')
        episode.setTVShowTitle('Carrie')
        episode.setSeason(1)
        episode.setEpisode(2)
        params = ParameterHandler()
        params.setParam('sUrl', 'serie/carrie/staffel-1/episode-2')
        cGui().addFolder(episode, params)
        route = dict(parse_qsl(urlsplit(listed[-1][1]).query))
        assert route['watchlistTarget'] == folder
        assert dict(parse_qsl(urlsplit(folder).query))['sUrl'] == 'serie/carrie?a=one&b=two'
        assert route['watchlistTitle'] in ('Carrie', 'Carrie (2026)')
        assert route['watchlistYear'] == '2026'
        history.record('Folge 2', mediaType='episode', season='1', episode='2', showTitle='Carrie',
                       target=folder, seriesTarget=folder, seriesTitle=route['watchlistTitle'], year=route['watchlistYear'])
    assert len(epicfavorites.watchEntries('watching')) == 1
    assert epicfavorites.watchEntries('watching')[0]['title'] == 'Carrie (2026)'


def test_watchlist_tracks_without_history_and_preserves_movie_folder(monkeypatch, tmp_path):
    from resources.lib import epicfavorites

    monkeypatch.setattr(epicfavorites, '_profilePath', lambda: str(tmp_path / 'favorites.json'))
    monkeypatch.setattr(history, '_historyPath', lambda: str(tmp_path / 'history.json'))
    set_setting('watchHistoryEnabled', 'false')
    target = 'plugin://plugin.video.gerxstream/?site=netzkino&function=showDetails&sUrl=movie'
    assert history.record('Film', target=target, targetIsFolder=True) is False
    entries = epicfavorites.watchEntries('watching')
    assert len(entries) == 1
    assert entries[0]['is_folder'] is True
    assert entries[0]['source'] == 'netzkino'
    assert history.entries() == []


def test_watchlist_status_changes_backup_and_copy_to_favorites(monkeypatch, tmp_path, real_strings):
    from resources.lib import epicfavorites
    from resources.lib.handler.ParameterHandler import ParameterHandler

    main = _main_module(monkeypatch)
    monkeypatch.setattr(epicfavorites, '_profilePath', lambda: str(tmp_path / 'favorites.json'))
    entry = {'title': 'Carrie (2026)', 'media_type': 'tvshow', 'is_folder': True,
             'target': 'plugin://plugin.video.gerxstream/?site=serienstream&function=showSeasons&sUrl=carrie'}
    for status in epicfavorites.STATUSES:
        assert epicfavorites.setStatus(entry, status)
        assert len(epicfavorites.watchEntries(status)) == 1
        assert sum(len(epicfavorites.watchEntries(key)) for key in epicfavorites.STATUSES) == 1
    stored = epicfavorites.watchEntries('dropped')[0]
    assert epicfavorites.createFolder('', 'Serien')
    folderId = epicfavorites.exportData()['folders'][0]['id']
    assert epicfavorites.createFolder(folderId, 'Drama')
    subfolderId = epicfavorites.exportData()['folders'][0]['folders'][0]['id']
    path = folderId + '/' + subfolderId
    monkeypatch.setattr(epicfavorites, 'chooseFolder', lambda: path)
    params = ParameterHandler()
    params.addParams({'entrySource': 'watchlist', 'entryId': stored['id']})
    main.addEpicFavorite(params)
    saved = epicfavorites.contents(path)[3]
    assert len(saved) == 1
    assert saved[0]['title'] == 'Carrie (2026)' and saved[0]['is_folder']
    exported = epicfavorites.exportData()
    assert epicfavorites.importData(exported)
    assert epicfavorites.exportData() == exported
    assert epicfavorites.removeWatchEntry(stored['id'])
    assert epicfavorites.watchEntries('dropped') == []
    assert len(epicfavorites.contents(path)[3]) == 1


def test_status_list_has_one_action_per_command(monkeypatch, tmp_path, real_strings):
    from resources.lib import epicfavorites
    from resources.lib.gui.gui import cGui

    main = _main_module(monkeypatch)
    monkeypatch.setattr(epicfavorites, '_profilePath', lambda: str(tmp_path / 'favorites.json'))
    assert epicfavorites.setStatus({'title': 'Carrie', 'media_type': 'tvshow', 'is_folder': True,
                                   'target': 'plugin://plugin.video.gerxstream/?site=serienstream&function=showSeasons'}, 'planned')
    listed = []
    monkeypatch.setattr(cGui, 'addFolder', lambda self, element, *args: listed.append(element))
    monkeypatch.setattr(cGui, 'setView', lambda *args: None)
    monkeypatch.setattr(cGui, 'setEndOfDirectory', lambda *args: None)
    main.showWatchlistStatus('planned')
    assert [context.getFunction() for context in listed[0].getContextItems()] == [
        'setWatchlistStatus', 'removeWatchlistEntry', 'addEpicFavorite']


# --- Cookie-Import ----------------------------------------------------------

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'


def test_parse_curl_bash():
    text = ("curl 'https://s.to/' \\\n  -H 'accept: text/html' \\\n"
            "  -b 'cf_clearance=abc.def-1=; PHPSESSID=xyz' \\\n  -H 'user-agent: %s'" % UA)
    cookie, userAgent = protection.parseBrowserExport(text)
    assert cookie == 'cf_clearance=abc.def-1=; PHPSESSID=xyz'
    assert userAgent == UA


def test_parse_curl_cmd_with_carets():
    text = ('curl ^"https://s.to/^" ^\n  -H ^"cookie: cf_clearance=a1^%^2Fb; x=1^" ^\n'
            '  -H ^"user-agent: Mozilla/5.0 (X11)^"')
    cookie, userAgent = protection.parseBrowserExport(text)
    assert cookie == 'cf_clearance=a1%2Fb; x=1'
    assert userAgent == 'Mozilla/5.0 (X11)'


def test_parse_request_headers_and_netscape_and_json():
    cookie, userAgent = protection.parseBrowserExport(
        'GET / HTTP/2\nHost: s.to\nUser-Agent: %s\nCookie: __ddg1_=q; __ddg2_=w\n' % UA)
    assert cookie == '__ddg1_=q; __ddg2_=w' and userAgent == UA
    cookie, _ = protection.parseBrowserExport(
        '# Netscape HTTP Cookie File\n.s.to\tTRUE\t/\tTRUE\t0\tcf_clearance\tzzz\n')
    assert cookie == 'cf_clearance=zzz'
    cookie, _ = protection.parseBrowserExport('[{"name": "cf_clearance", "value": "j", "domain": ".s.to"}]')
    assert cookie == 'cf_clearance=j'
    assert protection.parseBrowserExport('cf_clearance=1; b=2') == ('cf_clearance=1; b=2', '')
    assert protection.parseBrowserExport(UA) == ('', UA)
    assert protection.parseBrowserExport('   ') == ('', '')


def test_missing_protection_cookie_hint():
    assert protection.missingProtectionCookies('PHPSESSID=1')
    assert not protection.missingProtectionCookies('cf_clearance=1; a=2')


def test_cookie_assistant_stores_cookie_and_agent():
    from resources.lib import cookieassistant
    from resources.lib.config import cConfig
    ok, _message = cookieassistant._accept('serienstream', "curl 'https://s.to/' -H 'cookie: cf_clearance=v' -H 'user-agent: %s'" % UA)
    assert ok
    assert cConfig().getSetting('plugin_serienstream_bypassCookie') == 'cf_clearance=v'
    assert cConfig().getSetting('plugin_serienstream_bypassUserAgent') == UA
    ok, _message = cookieassistant._accept('serienstream', 'nur Text')
    assert not ok


def test_cookie_assistant_lists_protected_sources():
    from resources.lib import cookieassistant
    ids = [siteId for siteId, _name in cookieassistant.protectedSources()]
    assert 'serienstream' in ids and 'testplugin' not in ids


# --- Personen ----------------------------------------------------------------

def test_person_query_and_result_parsing():
    query = persondata.buildQuery([31, 5064], 'Directing')
    assert '"31" "5064"' in query and 'wdt:P57' in query
    payload = {'results': {'bindings': [
        {'tmdb': {'value': '5064'}, 'kind': {'value': 'oscars'}, 'n': {'value': '3'}},
        {'tmdb': {'value': '5064'}, 'kind': {'value': 'films'}, 'n': {'value': '75'}},
        {'tmdb': {'value': 'x'}, 'kind': {'value': 'films'}, 'n': {'value': '1'}},
    ]}}
    assert persondata.parseResult(payload) == {'5064': {'oscars': 3, 'films': 75}}


def test_person_counts_use_cache(monkeypatch):
    requests = []

    def fake(query):
        requests.append(query)
        return {'results': {'bindings': [
            {'tmdb': {'value': '1'}, 'kind': {'value': 'films'}, 'n': {'value': '9'}}]}}
    monkeypatch.setattr(persondata, '_request', fake)
    persondata._saveCache({})
    first = persondata.counts([1, 2])
    assert first['1']['films'] == 9 and first['2']['films'] == 0
    second = persondata.counts([1, 2])
    assert second['1']['films'] == 9 and len(requests) == 1


def test_people_sorting_by_films_and_awards(real_strings):
    from resources.lib import categories
    people = [{'id': 1, 'name': 'A', 'popularity': 50}, {'id': 2, 'name': 'B', 'popularity': 10},
              {'id': 3, 'name': 'C', 'popularity': 30}]
    extra = {'1': {'films': 10, 'oscars': 0, 'grammys': 0},
             '2': {'films': 80, 'oscars': 1, 'grammys': 0},
             '3': {'films': 20, 'oscars': 0, 'grammys': 4}}
    byFilms = sorted(people, key=lambda p: categories._personSortKey(p, 'films', extra))
    byAwards = sorted(people, key=lambda p: categories._personSortKey(p, 'awards', extra))
    assert [p['name'] for p in byFilms] == ['B', 'C', 'A']
    assert [p['name'] for p in byAwards] == ['C', 'B', 'A']
    assert '4' in categories._personLabel(people[2], 'awards', extra)
    assert categories._personLabel(people[0], 'popularity', extra) == 'A'


# --- Beschreibung ----------------------------------------------------------

def test_omdb_parsing():
    data = {'Response': 'True', 'imdbRating': '8.8', 'imdbVotes': '2,512,000',
            'Ratings': [{'Source': 'Internet Movie Database', 'Value': '8.8/10'},
                        {'Source': 'Rotten Tomatoes', 'Value': '87%'},
                        {'Source': 'Metacritic', 'Value': '74/100'}]}
    assert plotinfo.parseOmdb(data) == {'imdb': (8.8, 2512000), 'rottentomatoes': '87%', 'metacritic': '74'}
    assert plotinfo.parseOmdb({'Response': 'False', 'Error': 'Invalid API key!'}) == {}
    assert plotinfo.parseOmdb({'imdbRating': 'N/A'}) == {}


def test_plot_lines_and_append():
    meta = {'rating': 8.4, 'director': 'Christopher Nolan',
            'cast': [('Leonardo DiCaprio', 'Cobb', ''), ('Joseph Gordon-Levitt', 'Arthur', ''),
                     ('Elliot Page', 'Ariadne', ''), ('Tom Hardy', 'Eames', ''), ('Ken Watanabe', 'Saito', ''),
                     ('Cillian Murphy', 'Fischer', '')]}
    lines = plotinfo.buildLines(meta, {'imdb': (8.8, 1), 'rottentomatoes': '87%'})
    assert 'IMDb[/B] 8.8' in lines[0] and 'Rotten Tomatoes[/B] 87%' in lines[0] and 'TMDB[/B] 8.4' in lines[0]
    assert 'Christopher Nolan' in lines[1]
    assert 'Ken Watanabe' in lines[2] and 'Cillian Murphy' not in lines[2]
    assert plotinfo.appendTo('Ein Dieb.', ['x']) == 'Ein Dieb.\n\nx'
    assert plotinfo.appendTo('', ['x']) == 'x'
    tv = plotinfo.buildLines({'creator': 'Vince Gilligan'}, mediaType='tvshow')
    assert 'Vince Gilligan' in tv[0]


def test_omdb_without_key_does_not_request(monkeypatch):
    set_setting(plotinfo.OMDB_KEY_SETTING, '')
    assert plotinfo.omdbRatings('tt1375666') == {}
    set_setting(plotinfo.OMDB_KEY_SETTING, 'abc12345')
    assert plotinfo.omdbRatings('keine-id') == {}


def test_source_metadata_import_does_not_fetch_movie_catalog(monkeypatch):
    import os
    import runpy
    from resources.lib.handler.requestHandler import cRequestHandler

    set_setting('prefLanguage', '0')
    requests = []
    monkeypatch.setattr(cRequestHandler, 'request',
                        lambda self: requests.append(self) or '{"movies": []}')
    source = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sites', 'api_all.py')
    runpy.run_path(source)
    assert requests == []


def test_background_requests_restore_interactive_errors():
    from resources.lib.handler.requestHandler import cRequestHandler

    assert not cRequestHandler('https://example.org').ignoreErrors
    with cRequestHandler.backgroundRequests():
        assert cRequestHandler('https://example.org').ignoreErrors
        with cRequestHandler.backgroundRequests():
            assert cRequestHandler('https://example.org').ignoreErrors
        assert cRequestHandler('https://example.org').ignoreErrors
    assert not cRequestHandler('https://example.org').ignoreErrors


def test_static_setting_options_have_values_for_kodi_parser():
    from pathlib import Path
    from xml.etree import ElementTree

    settings_path = Path(__file__).resolve().parents[1] / 'resources' / 'settings.xml'
    settings = ElementTree.parse(settings_path)
    empty_options = [setting.get('id') for setting in settings.findall('.//setting')
                     for option in setting.findall('./constraints/options/option')
                     if not option.text or not option.text.strip()]

    assert empty_options == []


def _main_module(monkeypatch):
    import importlib
    import sys
    import types

    monkeypatch.setitem(sys.modules, 'resolveurl', types.ModuleType('resolveurl'))
    return importlib.import_module('gerxstream')


def test_saved_favorite_uses_provider_route_not_wrapper(monkeypatch, real_strings):
    import sys
    from resources.lib import epicfavorites
    from resources.lib.gui.gui import cGui
    from resources.lib.handler.ParameterHandler import ParameterHandler
    import xbmcplugin

    main = _main_module(monkeypatch)
    target = 'plugin://plugin.video.gerxstream/?site=serienstream&function=showSeasons&sUrl=serie/carrie'
    monkeypatch.setattr(epicfavorites, 'contents', lambda path: ('', {}, [], [{
        'id': 'a' * 32, 'title': 'Carrie (2026)', 'target': target,
        'is_folder': True, 'media_type': 'tvshow'}]))
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.gerxstream/', '1', ''])
    monkeypatch.setattr(cGui, '_cGui__createContextMenu', lambda self, element, item, *args: item)
    monkeypatch.setattr(cGui, 'setView', lambda *args: None)
    monkeypatch.setattr(cGui, 'setEndOfDirectory', lambda *args: None)
    added = []
    monkeypatch.setattr(xbmcplugin, 'addDirectoryItem', lambda *args: added.append(args))
    set_setting('autoNextEpisodeEnabled', 'true')
    params = ParameterHandler()
    params.setParam('section', 'favorites')
    main.showEpicFavorites(params)
    from urllib.parse import parse_qsl, urlsplit
    route = dict(parse_qsl(urlsplit(added[-1][1]).query))
    assert route['site'] == 'serienstream'
    assert route['function'] == 'showSeasons'
    assert route['sUrl'] == 'serie/carrie'
    assert route['watchlistTarget'] == epicfavorites.normaliseTarget(target)
    assert route['watchlistYear'] == '2026'
    assert added[-1][2]._label == 'Carrie (2026)'
    assert added[-1][3] is True


def test_selected_movie_does_not_match_anime_or_other_next_titles(monkeypatch):
    gerxstream = _main_module(monkeypatch)
    from resources.lib.gui.guiElement import cGuiElement
    from resources.lib.handler.ParameterHandler import ParameterHandler

    params = ParameterHandler()
    params.setParam('searchTitle', 'Next')
    params.setParam('searchYear', '2007')
    params.setParam('searchMedia', 'movie')
    for title, media, year, expected in (
            ('Next', 'movie', '2007', True),
            ('Next (2007)', 'movie', '', True),
            ('Next', 'movie', '2025', False),
            ('Next', 'tvshow', '', False),
            ('Boruto: Naruto Next Generations', 'tvshow', '', False),
            ('Meet Me Next Christmas', 'movie', '', False),
            ('Animes A-Z', '', '', False)):
        element = cGuiElement(title, 'source', 'showHosters')
        if media:
            element.setMediaType(media)
        if year:
            element.setYear(year)
        assert gerxstream._matchesSelectedTitle({'guiElement': element}, params) == expected


def test_missing_selected_movie_keeps_current_directory(monkeypatch, real_strings):
    gerxstream = _main_module(monkeypatch)
    from resources.lib.gui.gui import cGui
    from resources.lib.handler.ParameterHandler import ParameterHandler

    gui = cGui()
    ended = []
    messages = []
    monkeypatch.setattr(gui, 'setEndOfDirectory', lambda success=True: ended.append(success))
    monkeypatch.setattr(gerxstream, '_collectGlobalSearchResults', lambda *args: gui)
    monkeypatch.setattr(gerxstream.xbmcgui.Dialog, 'ok', lambda *args: messages.append(args))
    params = ParameterHandler()
    params.setParam('searchTitle', 'Next')
    assert gerxstream.searchTMDB(params) is False
    assert ended == [False]
    assert 'Next' in messages[0][-1]


def test_person_imdb_sort_modes_are_distinct():
    from resources.lib import categories

    people = [{'id': 1, 'name': 'Zoe'}, {'id': 2, 'name': 'Anna'}]
    scores = {'1': persondata.summarizeImdb([9.5, 4.0]),
              '2': persondata.summarizeImdb([8.0, 8.0])}
    assert sorted(people, key=lambda person: categories._personSortKey(person, 'name'))[0]['id'] == 2
    assert sorted(people, key=lambda person: categories._personSortKey(person, 'imdb_best', scores))[0]['id'] == 1
    assert sorted(people, key=lambda person: categories._personSortKey(person, 'imdb_average', scores))[0]['id'] == 2
    assert 'IMDb 9.50' in categories._personLabel(people[0], 'imdb_best', scores)


def test_person_groups_combine_industries_not_nationalities():
    from resources.lib import categories

    profiles = {'1': {'countries': ['US', 'IN']}, '2': {'countries': ['JP']}}
    assert categories._personInGroups({'id': 1}, {'hollywood', 'indian'}, profiles)
    assert not categories._personInGroups({'id': 2}, {'hollywood', 'indian'}, profiles)
    assert categories._personInGroups({'id': 2}, {'all'}, {})
    assert persondata.productionGroups(['US', 'FR']) == {'hollywood', 'other'}
    assert persondata.productionGroups([]) == set()


def test_people_limits_can_be_optional_and_independent():
    from resources.lib import categories

    set_setting('actorPeopleLimit', '100')
    set_setting('directorPeopleLimit', '0')
    assert categories._peopleLimit('Acting') == 100
    assert categories._peopleLimit('Directing') == 0


def test_settings_have_merged_index_and_separate_people_categories():
    import os
    import xml.etree.ElementTree as ET

    root = ET.parse(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'settings.xml'))
    categories = {category.get('id'): category for category in root.findall('.//category')}
    assert 'indexsite1' not in categories and 'indexsite2' not in categories
    assert categories['indexsites'].find(".//setting[@id='plugin_aniworld']") is not None
    assert categories['indexsites'].find(".//setting[@id='plugin_kkiste']") is not None
    for category, prefix in (('actors', 'actor'), ('directors', 'director')):
        assert categories[category].find(".//setting[@id='%sPeopleSort']" % prefix) is not None
        assert categories[category].find(".//setting[@id='%sPeopleGroupsPicker']" % prefix) is not None
        assert categories[category].find(".//setting[@id='%sPeopleLimit']/constraints/minimum" % prefix).text == '0'
    ids = [setting.get('id') for setting in root.findall('.//setting')]
    assert len(ids) == len(set(ids))


def test_people_settings_have_translations(real_strings):
    from resources.lib.config import cConfig

    for labelId in range(31600, 31623):
        assert cConfig().getLocalizedString(labelId) not in ('', str(labelId))


def test_body_read_timeout_is_quiet_in_background(monkeypatch):
    import types
    from resources.lib.handler import requestHandler

    messages = []
    closed = []

    def read():
        raise TimeoutError('The read operation timed out')

    response = types.SimpleNamespace(info=lambda: {}, read=read, close=lambda: closed.append(True))
    monkeypatch.setattr(requestHandler, 'build_opener', lambda *args: types.SimpleNamespace(open=lambda *args, **kwargs: response))
    monkeypatch.setattr(requestHandler.xbmcgui.Dialog, 'ok', lambda *args: messages.append(args))
    with requestHandler.cRequestHandler.backgroundRequests():
        assert requestHandler.cRequestHandler('https://example.test/movie', caching=False).request() == 'TIMEOUT'
    assert messages == [] and closed == [True]
    assert requestHandler.cRequestHandler('https://example.test/movie', caching=False).request() == 'TIMEOUT'
    assert len(messages) == 1 and closed == [True, True]


def test_empty_global_search_preserves_origin(monkeypatch):
    gerxstream = _main_module(monkeypatch)
    from resources.lib.gui.gui import cGui

    gui = cGui()
    ended = []
    monkeypatch.setattr(gui, 'setEndOfDirectory', lambda success=True: ended.append(success))
    monkeypatch.setattr(gerxstream, '_collectGlobalSearchResults', lambda *args: gui)
    assert gerxstream.searchGlobal('Next') is False
    assert ended == [False]


def test_film_profiles_cache_is_role_specific(monkeypatch):
    requests = []
    cache = {}
    monkeypatch.setattr(persondata, '_loadCache', lambda: cache)
    monkeypatch.setattr(persondata, '_saveCache', lambda data: cache.update(data))

    def request(query):
        requests.append(query)
        return {'results': {'bindings': [
            {'tmdb': {'value': '1'}, 'country': {'value': 'US'}, 'imdb': {'value': 'tt1234567'}},
            {'tmdb': {'value': '1'}, 'country': {'value': 'IN'}, 'imdb': {'value': 'tt1234567'}},
            {'tmdb': {'value': '1'}, 'imdb': {'value': 'invalid'}}]}}

    monkeypatch.setattr(persondata, '_request', request)
    actors = persondata.filmProfiles([1, 1, 2, 'invalid'])
    assert actors['1']['countries'] == ['IN', 'US']
    assert actors['1']['imdb_ids'] == ['tt1234567']
    assert actors['2']['countries'] == []
    assert persondata.filmProfiles([1])['1'] == actors['1']
    assert len(requests) == 1 and 'wdt:P161' in requests[0]
    persondata.filmProfiles([1], 'Directing')
    assert len(requests) == 2 and 'wdt:P57' in requests[1]


def test_film_profile_failure_is_not_cached(monkeypatch):
    monkeypatch.setattr(persondata, '_loadCache', lambda: {})
    monkeypatch.setattr(persondata, '_request', lambda query: {})
    saved = []
    monkeypatch.setattr(persondata, '_saveCache', lambda cache: saved.append(cache))
    assert persondata.filmProfiles([1]) == {}
    assert saved == []


def test_people_filter_and_sort_before_top_limit(monkeypatch):
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    set_setting('actorPeopleSort', 'name')
    set_setting('actorPeopleGroups', 'hollywood,indian')
    set_setting('actorPeopleLimit', '1')
    set_setting('directorPeopleSort', 'imdb_best')
    people = [{'id': 1, 'name': 'Zoe'}, {'id': 2, 'name': 'Anna'}, {'id': 3, 'name': 'Aaron'}]
    monkeypatch.setattr(categories.cTMDB, 'getUrl', lambda *args: {'results': people, 'total_pages': 1})
    monkeypatch.setattr(categories, 'favoriteActors', lambda: [])
    monkeypatch.setattr(persondata, 'filmProfiles', lambda *args: {
        '1': {'countries': ['US']}, '2': {'countries': ['IN']}, '3': {'countries': ['JP']}})
    listed = []
    monkeypatch.setattr(categories, '_addPersonFolder', lambda params, person, title: listed.append(person['name']) or True)
    params = ParameterHandler()
    params.setParam('catRole', 'Acting')
    categories._people(params)
    assert listed == ['Anna']


def test_people_sort_inherit_and_legacy_empty_keep_previous_sort(monkeypatch):
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    people = [{'id': 1, 'name': 'Zoe'}, {'id': 2, 'name': 'Anna'}]
    monkeypatch.setattr(categories.cTMDB, 'getUrl', lambda *args: {'results': people, 'total_pages': 1})
    monkeypatch.setattr(categories, 'favoriteActors', lambda: [])
    listed = []
    monkeypatch.setattr(categories, '_addPersonFolder', lambda params, person, title: listed.append(person['name']) or True)
    set_setting('peopleSort', 'name')

    for role, prefix in (('Acting', 'actor'), ('Directing', 'director')):
        for value in ('', 'inherit'):
            set_setting(prefix + 'PeopleSort', value)
            set_setting(prefix + 'PeopleLimit', '2')
            listed.clear()
            params = ParameterHandler()
            params.setParam('catRole', role)
            categories._people(params)
            assert listed == ['Anna', 'Zoe']


def test_random_and_category_settings_have_own_sidebar_pages():
    import xml.etree.ElementTree as ET
    from pathlib import Path

    root = ET.parse(Path(__file__).resolve().parents[1] / 'resources' / 'settings.xml').getroot()
    random_settings = root.find(".//category[@id='randommovies']")
    category_settings = root.find(".//category[@id='categories']")
    assert {setting.get('id') for setting in random_settings.findall('.//setting')} >= {
        'randomItemsCount', 'randomGenresPicker', 'randomExcludedGenres', 'randomMinImdb'}
    assert {setting.get('id') for setting in category_settings.findall('.//setting')} >= {
        'showCategories', 'categoryMinImdb', 'categoryMinTmdb', 'categoryMinVotes', 'categoryMediathekenAll'}
    ids = [setting.get('id') for setting in root.findall('.//setting')]
    assert len(ids) == len(set(ids))
    assert random_settings.find(".//setting[@id='randomItemsCount']/default").text == '250'


def test_random_menu_route_returns_before_scraper_dispatch(monkeypatch):
    import sys

    main = _main_module(monkeypatch)
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.gerxstream/', '1',
                                    '?site=random&function=randomMovies'])
    shown = []
    monkeypatch.setattr(main, 'showRandomMovies', lambda: shown.append(True))
    monkeypatch.setattr(main, '_isAllowedScraperRoute', lambda *args: (_ for _ in ()).throw(
        AssertionError('Unexpected scraper dispatch')))
    main.parseUrl()
    assert shown == [True]


def test_random_menu_does_not_fetch_movies(monkeypatch):
    from resources.lib import randommovies

    listed = []
    monkeypatch.setattr(randommovies.cTMDB, 'getUrl', lambda *args: (_ for _ in ()).throw(AssertionError('API called')))
    monkeypatch.setattr(randommovies, '_folder', lambda title, level, mode='', value='': listed.append((level, mode)))
    randommovies.showMenu()
    assert listed == [('entries', 'random'), ('genres', ''), ('companies', '')]


def test_imdb_filter_uses_actual_omdb_rating_and_rejects_missing(monkeypatch):
    set_setting('randomMinImdb', '8.0')
    assert plotinfo.minimumRating('randomMinImdb') == 8.0
    monkeypatch.setattr(plotinfo, 'omdbRatings', lambda imdb_id: {'imdb': (7.0, 123)})
    assert not plotinfo.matchesMinimum({'imdb_id': 'tt1234567', 'vote_average': 9.5}, 'movie', 8.0)
    monkeypatch.setattr(plotinfo, 'omdbRatings', lambda imdb_id: {'imdb': (8.0, 123)})
    assert plotinfo.matchesMinimum({'imdb_id': 'tt1234567', 'vote_average': 1.0}, 'movie', 8.0)
    assert not plotinfo.matchesMinimum({}, 'movie', 8.0)
    assert plotinfo.matchesMinimum({}, 'movie', 0)


def test_random_entry_route_preserves_metadata_and_cleans_up(monkeypatch, real_strings):
    import sys
    import types
    from resources.lib import randommovies

    main = _main_module(monkeypatch)
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.gerxstream/', '1',
                                    '?function=randomMovies&randomLevel=entries&randomMode=genre&randomValue=28'])
    set_setting('randomItemsCount', '2')
    closed = []
    updates = []
    canceled = [False]
    monkeypatch.setattr(randommovies.xbmcgui, 'DialogProgress', lambda: types.SimpleNamespace(
        create=lambda *args: None, update=updates.append,
        iscanceled=lambda: canceled[0], close=lambda: closed.append(True)), raising=False)
    monkeypatch.setattr(randommovies.xbmc, 'Monitor', lambda: types.SimpleNamespace(
        abortRequested=lambda: False), raising=False)
    items = [{'id': 1, 'title': 'Film A', 'original_title': 'Original A', 'release_date': '2007-01-01'},
             {'id': 2, 'title': 'Film B', 'release_date': '2020-01-01'}]
    monkeypatch.setattr(randommovies.cTMDB, 'getUrl', lambda *args: {'total_results': 2, 'results': items})
    added = []
    ended = []
    monkeypatch.setattr(randommovies.cGui, 'addFolder', lambda self, element, params, *args: added.append(
        (element.getFunction(), dict(params.getAllParameters()))))
    monkeypatch.setattr(randommovies.cGui, 'setEndOfDirectory', lambda self, success=True: ended.append(success))
    main.showRandomMovies()
    assert len(added) == 2 and closed == [True] and ended == [True]
    assert all(function == 'searchTMDB' for function, params in added)
    first = next(params for function, params in added if params['searchTmdbID'] == '1')
    assert first['searchYear'] == '2007' and first['searchOriginalTitle'] == 'Original A'
    assert first['searchMedia'] == 'movie'
    assert updates and all(0 <= update <= 100 for update in updates)
    added.clear()
    canceled[0] = True
    main.showRandomMovies()
    assert not added and ended[-1] is False and len(closed) == 2
    canceled[0] = False
    set_setting('randomExcludedGenres', '16')
    items[0]['genre_ids'] = [16, 28]
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.gerxstream/', '1',
                                    '?function=randomMovies&randomLevel=entries&randomMode=random'])
    main.showRandomMovies()
    assert len(added) == 1 and added[0][1]['searchTmdbID'] == '2'


def test_random_catalog_failure_and_cancel_do_not_fake_results():
    import pytest
    from resources.lib import randommovies

    class Unavailable:
        def getUrl(self, *args):
            return {}

    with pytest.raises(ValueError):
        randommovies.sampleCatalog(Unavailable(), '', 250)
    assert randommovies.sampleCatalog(Unavailable(), '', 250, canceled=lambda: True) == []


def test_random_genre_picker_preserves_cancel_and_allows_excluding_everything(monkeypatch):
    from resources.lib import randommovies

    set_setting('randomExcludedGenres', '16')
    monkeypatch.setattr(randommovies.xbmcgui.Dialog, 'multiselect', lambda *args, **kwargs: None)
    randommovies.editGenres()
    assert randommovies._excludedGenres() == {'16'}
    monkeypatch.setattr(randommovies.xbmcgui.Dialog, 'multiselect', lambda *args, **kwargs: [])
    randommovies.editGenres()
    assert randommovies._query('random', '') is None


def test_random_catalog_sampling_reaches_beyond_tmdb_page_limit(monkeypatch):
    from datetime import date
    from urllib.parse import parse_qs
    from resources.lib import randommovies

    calls = []

    class TMDB:
        def getUrl(self, path, page, extra):
            terms = parse_qs(extra)
            first = terms['primary_release_date.gte'][0]
            last = terms['primary_release_date.lte'][0]
            full = first == '2020-01-01' and last == '2020-01-04'
            total = 12000 if full else 6000
            base = 6000 if first == '2020-01-03' else 0
            calls.append((first, last, page))
            return {'total_results': total, 'results': [
                {'id': base + (page - 1) * 20 + offset + 1, 'title': 'Film'} for offset in range(20)]}

    monkeypatch.setattr(randommovies.random, 'sample', lambda population, count: [0, 11999])
    items = randommovies.sampleCatalog(TMDB(), 'include_adult=false', 2,
                                       start=date(2020, 1, 1), end=date(2020, 1, 4))
    assert {item['id'] for item in items} == {1, 12000}
    assert all(page <= 500 for first, last, page in calls)


def test_random_query_filters_are_whitelisted_and_mode_specific():
    from resources.lib import randommovies

    set_setting('randomExcludedGenres', '10751,16,bogus')
    assert 'without_genres=10751,16' in randommovies._query('random', '')
    assert 'vote_count' not in randommovies._query('random', '')
    assert 'without_genres' not in randommovies._query('genre', '28')
    assert 'with_companies=2' in randommovies._query('company', '2')
    assert randommovies._query('genre', '28&include_adult=true') is None
    assert randommovies._query('company', '999999') is None


def test_category_filters_and_exact_theme_matching(monkeypatch):
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    set_setting('categoryMinTmdb', '7.0')
    set_setting('categoryMinVotes', '100')
    items = [{'id': 1, 'vote_average': 8.0, 'vote_count': 200},
             {'id': 2, 'vote_average': 6.0, 'vote_count': 200},
             {'id': 3, 'vote_average': 9.0, 'vote_count': 5}]
    assert categories._filterItems(items, 0) == items[:1]
    monkeypatch.setattr(categories, 'KEYWORD_SEARCH_CACHE', {})
    monkeypatch.setattr(categories.cTMDB, 'getUrl', lambda *args: {'results': [{'id': 123, 'name': 'human nature'}]})
    assert categories._keywordIdByTerm('nature') == 0
    params = ParameterHandler()
    params.setParam('catPreset', 'kw:nature')
    assert categories._buildQuery(params)[0] is None
    monkeypatch.setattr(categories, '_keywordIdByTerm', lambda term: 456)
    path, extra, page = categories._buildQuery(params)
    assert path == 'discover/movie'
    assert 'with_genres=99' in extra
    assert 'with_keywords=456' in extra


def test_category_navigation_splits_charts_and_merges_collections(monkeypatch, real_strings):
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    listed = []
    monkeypatch.setattr(categories, '_addFolder', lambda title, function, params: listed.append(
        (title, params.getValue('catLevel'), params.getValue('catMedia'))))
    params = ParameterHandler()
    categories._charts(params)
    assert [(level, media) for title, level, media in listed] == [('chartList', 'movie'), ('chartList', 'tv')]
    listed.clear()
    params.setParam('catMedia', 'tv')
    categories._chartList(params)
    assert all(level == 'entries' and media == 'tv' for title, level, media in listed)
    assert len(listed) == len(categories.CHARTS)
    listed.clear()
    categories._root(params)
    assert not any(level in ('collections', 'ratings') for title, level, media in listed)
    assert listed[0][0] == 'Aktuelle Trends (Filme und Serien)'
    listed.clear()
    categories._keywords(params)
    titles = [title for title, level, media in listed]
    assert 'Marvel Cinematic Universe' in titles
    assert titles.count('Superhelden') == 1


def test_category_links_preserve_selected_film_metadata(monkeypatch):
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    item = {'id': 17350, 'title': 'Next', 'original_title': 'Next', 'release_date': '2007-04-25'}
    monkeypatch.setattr(categories.cTMDB, 'getUrl', lambda *args: {'results': [item]})
    collected = []
    monkeypatch.setattr(categories.cGui, 'addFolder', lambda self, element, params, *args: collected.append(
        {key: params.getValue(key) for key in ('searchTitle', 'searchOriginalTitle', 'searchYear', 'searchMedia', 'searchTmdbID')}))
    params = ParameterHandler()
    params.setParam('catMedia', 'movie')
    categories._entries(params)
    categories._indexAll(params)
    assert collected
    for selected in collected:
        assert selected == {'searchTitle': 'Next', 'searchOriginalTitle': 'Next', 'searchYear': '2007',
                            'searchMedia': 'movie', 'searchTmdbID': '17350'}


def test_director_movie_query_does_not_use_cast():
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    params = ParameterHandler()
    params.setParam('catPerson', '123')
    params.setParam('catRole', 'Directing')
    assert 'with_crew=123' in categories._buildQuery(params)[1]
    assert 'with_cast' not in categories._buildQuery(params)[1]


def test_imdb_scores_reuse_shared_film_ratings(monkeypatch):
    import types
    import xbmc
    import xbmcgui

    monkeypatch.setattr(xbmcgui, 'DialogProgress', lambda: types.SimpleNamespace(
        create=lambda *args: None, update=lambda *args: None,
        iscanceled=lambda: False, close=lambda: None), raising=False)
    monkeypatch.setattr(xbmc, 'Monitor', lambda: types.SimpleNamespace(abortRequested=lambda: False), raising=False)
    cache = {}
    requested = []
    profiles = {'1': {'imdb_ids': ['tt1234567', 'tt7654321']},
                '2': {'imdb_ids': ['tt7654321']}}
    monkeypatch.setattr(persondata, '_loadCache', lambda: cache)
    monkeypatch.setattr(persondata, '_saveCache', lambda data: cache.update(data))

    def ratings(imdbId):
        requested.append(imdbId)
        return {'imdb': (9.0 if imdbId == 'tt1234567' else 7.0, 100)}

    monkeypatch.setattr(plotinfo, 'omdbRatings', ratings)
    first = persondata.imdbScores([1, 2], profiles)
    assert first['1'] == {'imdb_best': 9.0, 'imdb_average': 8.0, 'imdb_count': 2}
    assert first['2']['imdb_average'] == 7.0
    assert sorted(requested) == ['tt1234567', 'tt7654321']
    assert persondata.imdbScores([1, 2], profiles) == first
    assert len(requested) == 2


def test_missing_imdb_key_preserves_list_without_fetching_people(monkeypatch):
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    set_setting('directorPeopleSort', 'imdb_best')
    requested = []
    ended = []
    monkeypatch.setattr(categories.cTMDB, 'getUrl', lambda *args: requested.append(args))
    monkeypatch.setattr(categories.cGui, 'setEndOfDirectory', lambda self, success=True: ended.append(success))
    params = ParameterHandler()
    params.setParam('catRole', 'Directing')
    categories._people(params)
    assert ended == [False] and requested == []


def test_groups_picker_supports_multiple_and_cancel(monkeypatch, real_strings):
    import xbmcgui
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    params = ParameterHandler()
    params.setParam('catRole', 'Acting')
    monkeypatch.setattr(xbmcgui.Dialog, 'multiselect', lambda *args, **kwargs: [0, 1, 5])
    categories.editPeopleGroups(params)
    assert categories._peopleGroups('Acting') == {'hollywood', 'indian'}
    assert categories._peopleGroups('Directing') == {'all'}
    monkeypatch.setattr(xbmcgui.Dialog, 'multiselect', lambda *args, **kwargs: None)
    categories.editPeopleGroups(params)
    assert categories._peopleGroups('Acting') == {'hollywood', 'indian'}


def test_plugin_worker_request_errors_stay_in_own_thread(monkeypatch):
    import sys
    import types
    from concurrent.futures import ThreadPoolExecutor
    from resources.lib.handler.requestHandler import cRequestHandler

    gerxstream = _main_module(monkeypatch)
    module = types.ModuleType('test_search_provider')
    module._search = lambda gui, text: gui.searchResults.append(
        {'quiet': cRequestHandler('https://example.test/movie').ignoreErrors})
    monkeypatch.setitem(sys.modules, module.__name__, module)
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(gerxstream._pluginSearch, {'id': module.__name__, 'name': 'Test'}, 'Next').result()
        assert result == [{'quiet': True}]
        assert executor.submit(lambda: cRequestHandler('https://example.test/').ignoreErrors).result() is False
    assert cRequestHandler('https://example.test/').ignoreErrors is False


def test_selected_movie_original_title_fallback_renders_only_matching_movie(monkeypatch):
    gerxstream = _main_module(monkeypatch)
    from resources.lib.gui.gui import cGui
    from resources.lib.gui.guiElement import cGuiElement
    from resources.lib.handler.ParameterHandler import ParameterHandler

    movie = cGuiElement('The Next Movie')
    movie.setMediaType('movie')
    movie.setYear('2007')
    other = cGuiElement('Boruto Naruto Next Generations')
    gui = cGui()
    attempts = []

    def collect(text, include):
        attempts.append(text)
        assert include({'globalsearch': 'true'})
        assert not include({'globalsearch': False})
        gui.searchResults = ([{'guiElement': movie}] if len(attempts) > 1 else [{'guiElement': other}])
        return gui

    monkeypatch.setattr(gerxstream, '_collectGlobalSearchResults', collect)
    rendered = []
    monkeypatch.setattr(gerxstream, '_renderCollectedSearchResults', lambda gui, results: rendered.extend(results) or True)
    params = ParameterHandler()
    for key, value in {'searchTitle': 'Der naechste Film', 'searchOriginalTitle': 'The Next Movie',
                       'searchYear': '2007', 'searchMedia': 'movie'}.items():
        params.setParam(key, value)
    assert gerxstream.searchTMDB(params) is True
    assert attempts == ['Der naechste Film', 'The Next Movie']
    assert rendered == [{'guiElement': movie}]
