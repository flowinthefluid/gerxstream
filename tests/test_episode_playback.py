# -*- coding: utf-8 -*-
"""A selected episode must start once while Kodi keeps the following episodes."""

import sys
import pytest
from urllib.parse import parse_qsl, urlsplit

from resources.lib.gui import hoster
from resources.lib import episodequeue, history, playbackstate


@pytest.mark.parametrize('enabled', [False, True])
def test_episode_directory_uses_start_action_only_when_enabled(monkeypatch, enabled):
    from resources.lib.gui.gui import cGui
    from resources.lib.gui.guiElement import cGuiElement
    from resources.lib.handler.ParameterHandler import ParameterHandler
    from conftest import set_setting
    set_setting('autoNextEpisodeEnabled', str(enabled).lower())
    set_setting('hosterSelect', 'List')
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.gerxstream/', '5', '?'])
    monkeypatch.setattr(cGui, '_episodeQueues', {})
    monkeypatch.setattr(cGui, '_cGui__createContextMenu',
                        lambda self, element, item, folder, url, episodeStartUrl='': item)
    listed = []
    stored = []
    monkeypatch.setattr(hoster.xbmcplugin, 'addDirectoryItem',
                        lambda handle, url, item, folder, total: listed.append((url, item, folder)))
    monkeypatch.setattr(episodequeue, 'store', lambda key, targets: stored.append(list(targets)))
    gui = cGui()
    for episode in range(1, 4):
        element = cGuiElement('Episode %d' % episode, 'aniworld', 'getHosters')
        element.setMediaType('episode')
        element.setTVShowTitle('Series')
        element.setSeason(1)
        element.setEpisode(episode)
        params = ParameterHandler()
        params.setParam('sUrl', 'https://example.test/episode/%d' % episode)
        gui.addFolder(element, params, bIsFolder=True)
    gui.setEndOfDirectory()
    assert len(stored[0]) == 3
    for index, (url, item, folder) in enumerate(listed):
        query = dict(parse_qsl(urlsplit(url).query))
        original = dict(parse_qsl(urlsplit(stored[0][index]).query))
        assert original['site'] == 'aniworld'
        assert original['episodeIndex'] == str(index)
        assert len(original['watchId']) == 64
        if enabled:
            assert original['playMode'] == 'play'
            assert original['mediaType'] == 'episode'
            assert original['MovieTitle'] == 'Episode %d' % (index + 1)
            assert query['site'] == 'cHosterGui'
            assert query['episodeStart'] == '1'
            assert item._props['IsPlayable'] == 'false'
            assert folder is False
        else:
            assert query['site'] == 'aniworld'
            assert 'episodeStart' not in query
            assert folder is True


def test_watched_flag_is_applied_to_directory_item(monkeypatch, tmp_path):
    from resources.lib.gui.gui import cGui
    from resources.lib.gui.guiElement import cGuiElement
    element = cGuiElement('Movie', 'source', 'getHosters')
    element.setMediaType('movie')
    key = playbackstate.itemKey('source', 'Movie')
    element.addItemProperties('GerXStream.WatchId', key)
    store = playbackstate.WatchedStore(str(tmp_path / 'watched.json'))
    store.mark(key)
    monkeypatch.setattr(playbackstate, '_watched', store)
    values = {}

    class VideoTag:
        def setUniqueID(self, value, provider):
            values['uniqueid'] = (value, provider)

        def setPlaycount(self, value):
            values['playcount'] = value

        def setResumePoint(self, *args):
            values['resume'] = args

    tag = VideoTag()
    monkeypatch.setattr(cGui, 'setInfoTagVideo', lambda *args: None)
    monkeypatch.setattr(hoster.xbmcgui.ListItem, 'getVideoInfoTag', lambda self: tag)
    cGui().createListItem(element)
    assert values == {'uniqueid': (key, 'gerxstream'), 'playcount': 1, 'resume': (0, 0)}


def test_single_episode_queue_is_kept(monkeypatch, tmp_path):
    monkeypatch.setattr(episodequeue, '_path', lambda: str(tmp_path / 'queues.json'))
    target = 'plugin://plugin.video.gerxstream/?site=aniworld&episode=1'
    assert episodequeue.store('f' * 32, [target]) is True
    assert episodequeue.getTargets('f' * 32) == [target]


def test_episode_action_starts_a_native_playlist_at_selected_episode(monkeypatch):
    targets = ['plugin://plugin.video.gerxstream/?episode=%d' % index
               for index in range(4)]
    queued = []
    starts = []
    window = hoster.xbmcgui.Window(10000)

    class Playlist:
        def clear(self):
            queued.clear()

        def add(self, url, item):
            queued.append((url, item))

    class Params:
        def getValue(self, name):
            return {'episodeStart': '1', 'episodeQueue': 'e' * 32,
                    'episodeIndex': '2'}.get(name, '')

    playlist = Playlist()
    monkeypatch.setattr(hoster, 'ParameterHandler', Params)
    monkeypatch.setattr(hoster.xbmc, 'PlayList', lambda _kind: playlist)
    monkeypatch.setattr(hoster.xbmc, 'Player', lambda: type('Player', (), {
        'play': lambda self, item: starts.append(item)})())
    monkeypatch.setattr(episodequeue, 'getTargets', lambda _key: targets)
    from conftest import set_setting
    set_setting('autoNextEpisodeEnabled', 'true')
    try:
        assert hoster.cHosterGui().play() is True
        assert [url for url, _item in queued] == targets[2:]
        assert starts == [playlist]
        assert all(item._props['ForceResolvePlugin'] == 'true' for _url, item in queued)
    finally:
        window.clearProperty(hoster.cHosterGui.EPISODE_PLAYLIST_PROPERTY)


def test_episode_queue_seeds_an_empty_kodi_playlist(monkeypatch):
    targets = ['plugin://plugin.video.gerxstream/?episode=%d' % index
               for index in range(3)]
    queued = []
    window = hoster.xbmcgui.Window(10000)
    window.clearProperty(hoster.cHosterGui.EPISODE_PLAYLIST_PROPERTY)

    class Playlist:
        def size(self):
            return len(queued)

        def getposition(self):
            return -1

        def add(self, url, item):
            queued.append((url, item))

    class Params:
        def getValue(self, name):
            return {'episodeQueue': 'd' * 32, 'episodeIndex': '0'}.get(name, '')

    class Config:
        def getSettingBool(self, _name, default):
            return True

    monkeypatch.setattr(hoster, 'cConfig', Config)
    monkeypatch.setattr(hoster.xbmc, 'PlayList', lambda _kind: Playlist())
    monkeypatch.setattr(episodequeue, 'getTargets', lambda _key: targets)

    try:
        assert hoster.cHosterGui._queueFollowingEpisodes(Params()) is True
        assert [url for url, _item in queued] == targets
    finally:
        window.clearProperty(hoster.cHosterGui.EPISODE_PLAYLIST_PROPERTY)


def test_episode_resolves_once_and_appends_following_items(monkeypatch):
    targets = ['plugin://plugin.video.gerxstream/?episode=%d' % i for i in range(3)]
    queued = [(targets[0], object())]
    resolved = []
    direct_starts = []
    window = hoster.xbmcgui.Window(10000)
    window.clearProperty(hoster.cHosterGui.EPISODE_PLAYLIST_PROPERTY)

    class Playlist:
        position = 0

        def size(self):
            return len(queued)

        def getposition(self):
            return self.position

        def add(self, url, item):
            queued.append((url, item))

        def clear(self):
            raise AssertionError('Kodi already placed the selected episode in the playlist')

    playlist = Playlist()

    class Params:
        index = '0'

        def getValue(self, name):
            return {'episodeQueue': 'a' * 32, 'episodeIndex': self.index,
                    'mediaType': 'episode'}.get(name, '')

    params = Params()

    class Config:
        def getSettingInt(self, _name, default):
            return default

        def getSettingBool(self, _name, default):
            return True

    class Gui:
        pluginHandle = 5

    class Player:
        def startPlayer(self):
            return True

    monkeypatch.setattr(hoster, 'ParameterHandler', lambda: params)
    monkeypatch.setattr(hoster, 'cConfig', Config)
    monkeypatch.setattr(hoster, 'cGui', Gui)
    monkeypatch.setattr(hoster, 'cPlayer', Player)
    monkeypatch.setattr(hoster.xbmc, 'PlayList', lambda _kind: playlist)
    monkeypatch.setattr(hoster.xbmc, 'Player', lambda: type('KodiPlayer', (), {
        'play': lambda self, *args: direct_starts.append(args)})())
    monkeypatch.setattr(hoster.xbmc, 'getInfoLabel', lambda _name: '22.0')
    monkeypatch.setattr(hoster.xbmcplugin, 'setResolvedUrl',
                        lambda *args: resolved.append(args))
    monkeypatch.setattr(episodequeue, 'getTargets', lambda _key: targets)
    monkeypatch.setattr(history, 'record', lambda *args: None)
    monkeypatch.setattr(hoster.cHosterGui, '_getInfoAndResolve',
                        lambda self, _result: {
                            'link': 'https://example.test/episode.mp4', 'title': 'Episode',
                            'thumb': '', 'showTitle': '', 'episode': '', 'season': '',
                        })

    gui = hoster.cHosterGui()
    assert gui.play({'streamUrl': ''}) is True
    assert [url for url, _ in queued] == targets
    assert len(resolved) == 1
    assert direct_starts == []
    assert window.getProperty(gui.EPISODE_PLAYLIST_PROPERTY).startswith('a' * 32 + ':0:')

    # Kodi invokes the add-on again for the next plugin:// playlist item.
    params.index = '1'
    playlist.position = 1
    assert gui.play({'streamUrl': ''}) is True
    assert [url for url, _ in queued] == targets
    assert len(resolved) == 2
    assert direct_starts == []
    window.clearProperty(gui.EPISODE_PLAYLIST_PROPERTY)


def test_stale_marker_does_not_turn_manual_episode_into_playlist_item(monkeypatch):
    queue_id = 'b' * 32
    window = hoster.xbmcgui.Window(10000)
    window.setProperty(hoster.cHosterGui.EPISODE_PLAYLIST_PROPERTY,
                       '%s:0:live-marker' % queue_id)

    class Playlist:
        def size(self):
            return 8

        def getposition(self):
            # This is the position left by a stopped old playback, not the
            # relative position of manually selected episode six.
            return 4

    class Params:
        def getValue(self, name):
            return {'episodeQueue': queue_id, 'episodeIndex': '6'}.get(name, '')

    monkeypatch.setattr(hoster.xbmc, 'PlayList', lambda _kind: Playlist())
    assert hoster.cHosterGui._isNativeEpisodePlaylistItem(Params()) is False
    window.clearProperty(hoster.cHosterGui.EPISODE_PLAYLIST_PROPERTY)


def test_legacy_marker_is_discarded_before_a_manual_selection(monkeypatch):
    queue_id = 'c' * 32
    window = hoster.xbmcgui.Window(10000)
    window.setProperty(hoster.cHosterGui.EPISODE_PLAYLIST_PROPERTY,
                       '%s:0' % queue_id)

    class Params:
        def getValue(self, name):
            return {'episodeQueue': queue_id, 'episodeIndex': '1'}.get(name, '')

    assert hoster.cHosterGui._isNativeEpisodePlaylistItem(Params()) is False
    assert window.getProperty(hoster.cHosterGui.EPISODE_PLAYLIST_PROPERTY) == ''
