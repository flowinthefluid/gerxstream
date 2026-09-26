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
    assert 'ARD Mediathek' in titles and 'MediathekViewWeb' in titles
    assert any(title.startswith('ZDF') for title in titles)
    assert any(title.startswith('ORF') for title in titles)
    assert any(title.startswith('phoenix') for title in titles)
    assert all(entry[1] in ('ardmediathek', 'mediathekviewweb') for entry in added)
