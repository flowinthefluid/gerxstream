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
