# -*- coding: utf-8 -*-
"""A selected episode must start once while Kodi keeps the following episodes."""

from resources.lib.gui import hoster
from resources.lib import episodequeue, history


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
