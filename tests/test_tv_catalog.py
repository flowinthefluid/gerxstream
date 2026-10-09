# -*- coding: utf-8 -*-
"""Live-TV-Katalog (DACH), Pluto-TV-Provider und Mediatheken-Ordner."""

import json
import os

from resources.lib.livestreams import model
from resources.lib.livestreams.providers import pluto

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CATALOG = os.path.join(_ROOT, 'resources', 'livestreams', 'sources', 'tv_dach.json')


def _catalog():
    with open(_CATALOG, encoding='utf-8') as handle:
        return json.load(handle)['channels']


def test_catalog_channels_are_valid_and_official():
    channels = _catalog()
    assert len(channels) > 150
    for raw in channels:
        channel = model.normalize_channel(raw)
        assert channel, raw['name']
        assert channel['nsfw'] is False
        for source in channel['sources']:
            assert source['rights_status'] == model.RIGHTS_APPROVED
            assert source['active']


def test_catalog_contains_public_channels_and_excludes_restreams():
    names = set(c['name'] for c in _catalog())
    for expected in ('Das Erste HD', 'ZDF', 'ZDFneo', 'ZDFinfo', '3sat', 'phoenix', 'KiKA',
                     'tagesschau24', 'ARD-alpha', 'WELT', 'ORF III HD', 'ServusTV', 'Red Bull TV'):
        assert expected in names, expected
    hosts = ' '.join(s['url'] for c in _catalog() for s in c['sources'])
    for denied in ('antik.sk', 'streamhostingcdn.top', 'freeott.top', 'rttv.com', 'jmp2.uk'):
        assert denied not in hosts
    assert not any('NFL' in n or 'Baseball' in n for n in names)


def test_orf_is_marked_geo_restricted_and_sports_have_own_section():
    channels = dict((c['name'], c) for c in _catalog() if c['country'] == 'at')
    assert channels['ORF III HD']['sources'][0]['geo_restricted']
    assert any(c['section'] == 'sports' and c['name'] == 'Red Bull TV' for c in _catalog())


RAW = [
    {'id': 'a' * 24, 'name': 'Kommissar Rex', 'images': [{'type': 'colorLogoPNG', 'url': 'https://images.pluto.tv/x.png'}]},
    {'id': 'b' * 24, 'name': 'DAZN Darts x Pluto TV', 'images': []},
    {'id': 'c' * 24, 'name': 'NFL Channel', 'images': []},
    {'id': 'd' * 24, 'name': 'Auto Motor Sport', 'images': []},
    {'id': 'e' * 24, 'name': 'Pluto TV Heiße Nächte', 'images': []},
    {'id': 'kaputt', 'name': 'Ungueltig'},
]
CATEGORIES = [
    {'name': 'Crime', 'channelIDs': ['a' * 24]},
    {'name': 'Live Sports', 'channelIDs': ['b' * 24, 'c' * 24]},
    {'name': 'Sinnliche Fantasien', 'channelIDs': ['e' * 24]},
]


def test_pluto_channels_are_built_and_filtered():
    built = dict((c['name'], c) for c in pluto.build_channels(RAW, CATEGORIES, 'de'))
    assert set(built) == {'Kommissar Rex', 'DAZN Darts x Pluto TV', 'Auto Motor Sport', 'Pluto TV Heiße Nächte'}
    assert built['DAZN Darts x Pluto TV']['section'] == 'sports'
    assert built['Auto Motor Sport']['section'] == 'sports'      # Racing ueber den Namen
    assert built['Kommissar Rex']['section'] == 'tv'
    assert built['Kommissar Rex']['logo'].endswith('x.png')
    assert built['Pluto TV Heiße Nächte']['nsfw'] is True
    for channel in built.values():
        normalized = model.normalize_channel(channel)
        assert normalized['sources'][0]['resolver'] == 'pluto'
        assert normalized['sources'][0]['rights_status'] == model.RIGHTS_APPROVED


def test_pluto_url_is_resolved_with_fresh_session(monkeypatch):
    monkeypatch.setattr(pluto, 'session', lambda force=False: {
        'token': 'tok/en', 'params': 'appName=web&country=DE', 'stitcher': 'https://stitcher.pluto.tv'})
    url = pluto.resolve_url('a' * 24)
    assert url.startswith('https://stitcher.pluto.tv/v2/stitch/hls/channel/%s/master.m3u8?appName=web' % ('a' * 24))
    assert 'jwt=tok%2Fen' in url
    assert pluto.resolve_url('../evil') == ''
    stored = pluto.build_channels(RAW[:1], [], 'de')[0]['sources'][0]['url']
    assert pluto.channel_id_from_url(stored) == 'a' * 24


def test_route_uses_resolved_pluto_url(monkeypatch):
    from resources.lib.livestreams import route
    monkeypatch.setattr(pluto, 'resolve_url', lambda cid: 'https://fresh/%s.m3u8' % cid)
    channel = model.normalize_channel(pluto.build_channels(RAW[:1], [], 'de')[0])
    item = route._list_item_for(channel, channel['sources'][0])
    assert item.getPath() == 'https://fresh/%s.m3u8' % ('a' * 24)


def test_m3u_export_uses_addon_route_for_session_sources():
    from resources.lib.livestreams import m3u
    channel = model.normalize_channel(pluto.build_channels(RAW[:1], [], 'de')[0])
    assert m3u._direct_url(channel).startswith('plugin://plugin.video.gerxstream/')


def test_mediatheken_folder_lists_sources_and_channels(monkeypatch, real_strings):
    from resources.lib import categories
    added = []

    class Gui(object):
        def addFolder(self, element, params=None, *args, **kwargs):
            added.append((element.getTitle(), element.getSiteName(), element.getFunction()))

        def setEndOfDirectory(self, *args):
            pass

        def showInfo(self, *args):
            added.append(('info',))

    class Handler(object):
        def getAvailablePlugins(self):
            return [{'id': 'ardmediathek', 'name': 'ARD Mediathek'}, {'id': 'mediathekviewweb', 'name': 'MediathekViewWeb'}]

    monkeypatch.setattr(categories, 'cGui', Gui)
    monkeypatch.setattr('resources.lib.handler.pluginHandler.cPluginHandler', Handler)
    categories._mediatheken(None)
    titles = [entry[0] for entry in added]
    assert 'ARD Mediathek' in titles and 'MediathekViewWeb' in titles and 'arte' in titles
    assert any(title.startswith('ZDF') for title in titles)
    assert any(title.startswith('ORF') for title in titles)
    assert any(title.startswith('phoenix') for title in titles)
    assert 'Netzkino' in titles
    assert all(entry[1] in categories.MEDIATHEK_SITES for entry in added)
    assert all(entry[2] == 'showChannel' for entry in added
               if entry[0].startswith('ZDF'))

    added.clear()
    from conftest import set_setting
    set_setting('categoryMediathekenAll', 'false')
    categories._mediatheken(None)
    assert 'arte' not in [entry[0] for entry in added]


def test_mediathek_channel_has_navigation(monkeypatch, real_strings):
    import sys
    from sites import mediathekviewweb
    added = []

    class Gui:
        def addFolder(self, element, params):
            added.append((element.getFunction(), dict(params.getAllParameters())))

        def setEndOfDirectory(self):
            pass

    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?mvwValue=ZDF'])
    monkeypatch.setattr(mediathekviewweb, 'cGui', Gui)
    mediathekviewweb.showChannel()
    assert [function for function, params in added] == ['showEntries', 'showGenre', 'showSearch']
    assert all(params['mvwChannel'] == 'ZDF' for function, params in added)


def test_mediathek_topic_query_keeps_channel(monkeypatch):
    import json
    from sites import mediathekviewweb
    payloads = []

    class Request:
        def __init__(self, url, **kwargs):
            payloads.append(json.loads(kwargs['data']))

        def addHeaderEntry(self, *args):
            pass

        def request(self):
            return '{"result":{"results":[],"queryInfo":{"totalResults":0}}}'

    monkeypatch.setattr(mediathekviewweb, 'cRequestHandler', Request)
    mediathekviewweb._query('topic', 'natur', 2, channel='ZDF')
    assert payloads[0]['queries'] == [
        {'fields': ['channel'], 'query': 'ZDF'},
        {'fields': ['topic', 'title'], 'query': 'natur'}]
    assert payloads[0]['offset'] == 100


def test_mediathek_global_search_ignores_channel(monkeypatch):
    import sys
    from sites import mediathekviewweb
    channels = []

    def query(mode, value, page, gui, channel=''):
        channels.append(channel)
        return [], 0

    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?mvwChannel=ZDF'])
    monkeypatch.setattr(mediathekviewweb, '_query', query)
    mediathekviewweb.showEntries(sGui=object(), sSearchText='Natur')
    assert channels == ['']


def test_arte_retains_collection_tiles():
    from sites import arte
    collection = {'title': 'Filmklassiker', 'programId': 'RC-028280',
                  'kind': {'code': 'TOPIC', 'isCollection': True}}
    payload = {'zones': [{'id': 'themes', 'content': {'data': [collection]}}]}
    assert arte._collectItems(payload, 'themes') == [collection]


def test_arte_collection_is_folder_not_player(monkeypatch):
    import sys
    from sites import arte
    added = []
    collection = {'title': 'Filmklassiker', 'programId': 'RC-028280',
                  'kind': {'code': 'TOPIC', 'isCollection': True}}

    class Gui:
        def addFolder(self, element, params, folder, total):
            added.append((element.getFunction(), dict(params.getAllParameters()), folder))

        def setView(self, *args):
            pass

        def setEndOfDirectory(self):
            pass

    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?sUrl=test&sZone=themes'])
    monkeypatch.setattr(arte, 'cGui', Gui)
    monkeypatch.setattr(arte, '_getJson', lambda *args: {
        'zones': [{'id': 'themes', 'content': {'data': [collection]}}]})
    arte.showEntries()
    assert added[0][0] == 'showGenre' and added[0][2]
    assert added[0][1]['sUrl'] == arte.URL_COLLECTION % 'RC-028280'
    assert added[0][1]['sZone'] == ''


def test_ard_embeds_teasers_without_losing_pagination():
    from urllib.parse import parse_qs, urlsplit
    from sites import ardmediathek
    url = ardmediathek.URL_MAIN + '/page-gateway/widgets/ard/test?embedded=false&pageNumber=2'
    query = parse_qs(urlsplit(ardmediathek._embeddedUrl(url)).query)
    assert query == {'embedded': ['true'], 'pageNumber': ['2']}
    assert ardmediathek._embeddedUrl(ardmediathek.URL_SEARCH % 'Natur') == ardmediathek.URL_SEARCH % 'Natur'


def test_ard_series_target_opens_grouping(monkeypatch):
    import sys
    from sites import ardmediathek
    added = []
    target = ardmediathek.URL_MAIN + '/page-gateway/pages/one/grouping/series?embedded=true'

    class Gui:
        def addFolder(self, element, params, folder, total):
            added.append((element.getFunction(), dict(params.getAllParameters()), folder))

        def setView(self, *args):
            pass

        def setEndOfDirectory(self):
            pass

    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?sUrl=test'])
    monkeypatch.setattr(ardmediathek, 'cGui', Gui)
    monkeypatch.setattr(ardmediathek, '_getJson', lambda *args: {'teasers': [
        {'shortTitle': 'Serie', 'links': {'target': {
            'id': 'series', 'type': 'application/vnd.ard.page+json', 'href': target}}}]})
    ardmediathek.showEntries()
    assert added[0] == ('showGenre', {'sUrl': target}, True)
    added.clear()
    ardmediathek.showEntries(sGui=Gui())
    assert added == []
