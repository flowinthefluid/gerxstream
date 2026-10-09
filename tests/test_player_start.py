# -*- coding: utf-8 -*-
"""The plugin must wait for the decoder callback before completing playback."""

import json
import pytest

from resources.lib import player
from resources.lib import playbackstate


@pytest.fixture
def monitored_playback(monkeypatch, tmp_path):
    window = playbackstate.xbmcgui.Window(10000)
    window.clearProperty(playbackstate.PLAYBACK_PROPERTY)
    window.clearProperty(player.EPISODE_PLAYLIST_PROPERTY)
    store = playbackstate.WatchedStore(str(tmp_path / 'watched.json'))
    monitor = playbackstate.PlaybackMonitor(store)
    state = {'playing': True, 'stream': 'https://example.test/first',
             'time': 0, 'total': 1000}
    monkeypatch.setattr(monitor, 'isPlayingVideo', lambda: state['playing'])
    monkeypatch.setattr(monitor, 'getPlayingFile', lambda: state['stream'], raising=False)
    monkeypatch.setattr(monitor, 'getTime', lambda: state['time'])
    monkeypatch.setattr(monitor, 'getTotalTime', lambda: state['total'])
    from resources.lib import history
    monkeypatch.setattr(history, 'record', lambda **kwargs: True)
    yield monitor, store, state, window
    window.clearProperty(playbackstate.PLAYBACK_PROPERTY)
    window.clearProperty(player.EPISODE_PLAYLIST_PROPERTY)


def _playback_context(key, stream, token='current', playlist=''):
    return json.dumps({'token': token, 'watch_id': key, 'stream': stream,
                       'playlist': playlist, 'history': {'title': 'Episode'}})


def test_service_keeps_sampling_after_plugin_return(monkeypatch, monitored_playback):
    monitor, store, state, window = monitored_playback
    key = playbackstate.itemKey('source', 'Episode')
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(key, state['stream']))
    samples = [899, 900, 999]
    state['time'] = samples[0]
    marks = []
    original_mark = store.mark
    monkeypatch.setattr(store, 'mark', lambda value: marks.append(value) or original_mark(value))

    class Monitor:
        position = 0

        def abortRequested(self):
            return False

        def waitForAbort(self, timeout):
            assert timeout == 0.5
            self.position += 1
            if self.position >= len(samples):
                return True
            state['time'] = samples[self.position]
            return False

    monkeypatch.setattr(playbackstate.xbmc, 'Monitor', Monitor)
    monitor.run()
    assert marks == [key]
    assert store.contains(key) is True


def test_next_episode_is_not_marked_by_old_stream_progress(monitored_playback):
    monitor, store, state, window = monitored_playback
    first = playbackstate.itemKey('source', 'First')
    second = playbackstate.itemKey('source', 'Second')
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(first, state['stream'], 'first'))
    state['time'] = 800
    monitor.tick()
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(second, 'https://example.test/second', 'second'))
    state['time'] = 950
    monitor.tick()
    assert store.contains(first) is True
    assert store.contains(second) is False
    state.update(stream='https://example.test/second', time=0)
    monitor.tick()
    assert monitor.context['watch_id'] == second
    assert monitor.marked is False


def test_stop_keeps_watched_flag_but_clears_own_episode_queue(monitored_playback):
    monitor, store, state, window = monitored_playback
    key = playbackstate.itemKey('source', 'Episode')
    marker = 'queue:0:current'
    window.setProperty(player.EPISODE_PLAYLIST_PROPERTY, marker)
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(key, state['stream'], playlist=marker))
    state['time'] = 900
    monitor.tick()
    state['playing'] = False
    monitor.onPlayBackStopped()
    assert store.contains(key) is True
    assert window.getProperty(playbackstate.PLAYBACK_PROPERTY) == ''
    assert window.getProperty(player.EPISODE_PLAYLIST_PROPERTY) == ''


@pytest.mark.parametrize('elapsed', [899, 900, 999])
def test_stop_does_not_restart_directory_loading(monkeypatch, monitored_playback, elapsed):
    monitor, store, state, window = monitored_playback
    key = playbackstate.itemKey('source', 'Episode')
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(key, state['stream']))
    commands = []
    monkeypatch.setattr(playbackstate.xbmc, 'executebuiltin',
                        lambda *args: commands.append(args))
    monkeypatch.setattr(playbackstate.xbmc, 'getInfoLabel',
                        lambda name: 'plugin://plugin.video.gerxstream/?site=source&function=showEpisodes'
                        if name == 'Container.FolderPath' else '')
    monkeypatch.setattr(playbackstate.xbmc, 'getCondVisibility', lambda _condition: False)
    state['time'] = elapsed
    monitor.tick()
    assert commands == []
    assert store.contains(key) is (elapsed >= 900)
    state['playing'] = False
    monitor.onPlayBackStopped()
    monitor.tick()
    monitor.tick()
    assert commands == []
    assert store.contains(key) is (elapsed >= 900)


def test_delayed_stop_preserves_pending_new_queue(monitored_playback):
    monitor, store, state, window = monitored_playback
    first = playbackstate.itemKey('source', 'First')
    second = playbackstate.itemKey('source', 'Second')
    window.setProperty(player.EPISODE_PLAYLIST_PROPERTY, 'old:0:marker')
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(first, state['stream'], 'first', 'old:0:marker'))
    monitor.tick()
    window.setProperty(player.EPISODE_PLAYLIST_PROPERTY, 'new:0:marker')
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(second, 'https://example.test/second', 'second', 'new:0:marker'))
    monitor.onPlayBackStopped()
    assert window.getProperty(player.EPISODE_PLAYLIST_PROPERTY) == 'new:0:marker'
    assert json.loads(window.getProperty(playbackstate.PLAYBACK_PROPERTY))['token'] == 'second'
    assert store.contains(second) is False


def test_episode_end_keeps_queue_even_when_position_already_advanced(monkeypatch, monitored_playback):
    monitor, store, state, window = monitored_playback
    key = playbackstate.itemKey('source', 'Episode')
    marker = 'queue:0:current'
    window.setProperty(player.EPISODE_PLAYLIST_PROPERTY, marker)
    context = json.loads(_playback_context(key, state['stream'], playlist=marker))
    context['has_next'] = True
    window.setProperty(playbackstate.PLAYBACK_PROPERTY, json.dumps(context))
    monitor.tick()
    playlist = type('Playlist', (), {'getposition': lambda self: 1, 'size': lambda self: 2})()
    monkeypatch.setattr(playbackstate.xbmc, 'PlayList', lambda _kind: playlist)
    state['playing'] = False
    monitor.onPlayBackEnded()
    assert window.getProperty(player.EPISODE_PLAYLIST_PROPERTY) == marker


def test_delayed_end_does_not_finish_already_playing_next_episode(monitored_playback):
    monitor, store, state, window = monitored_playback
    key = playbackstate.itemKey('source', 'Next episode')
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(key, state['stream'], 'next'))
    monitor.tick()
    monitor.onPlayBackEnded()
    assert monitor.context['token'] == 'next'
    assert window.getProperty(playbackstate.PLAYBACK_PROPERTY)


def test_seeking_to_credits_marks_current_episode(monitored_playback):
    monitor, store, state, window = monitored_playback
    key = playbackstate.itemKey('source', 'Episode')
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(key, state['stream']))
    monitor.tick()
    monitor.onPlayBackSeek(900000, 900000)
    assert store.contains(key) is True


def test_redirected_stream_uses_original_watch_id(monkeypatch, monitored_playback):
    monitor, store, state, window = monitored_playback
    key = playbackstate.itemKey('source', 'Episode')
    window.setProperty(playbackstate.PLAYBACK_PROPERTY,
                       _playback_context(key, 'https://example.test/original'))
    tag = type('Tag', (), {'getUniqueID': lambda self, provider: key})()
    monkeypatch.setattr(monitor, 'getVideoInfoTag', lambda: tag, raising=False)
    state['time'] = 900
    monitor.tick()
    assert store.contains(key) is True


def test_tagged_direct_video_is_watched_without_hoster_context(monkeypatch, monitored_playback):
    monitor, store, state, window = monitored_playback
    key = playbackstate.itemKey('doku_youtube', 'Video')
    tag = type('Tag', (), {'getUniqueID': lambda self, provider: key})()
    monkeypatch.setattr(monitor, 'getVideoInfoTag', lambda: tag, raising=False)
    state['time'] = 900
    monitor.tick()
    assert store.contains(key) is True


def test_watched_threshold_persists_at_90_percent_not_before(monkeypatch, tmp_path):
    store = playbackstate.WatchedStore(str(tmp_path / 'watched.json'))
    monitor = playbackstate.PlaybackMonitor(store)
    key = playbackstate.itemKey('source', 'Episode', '1', '2', 'Series')
    monitor.context = {'token': 'current', 'watch_id': key, 'stream': 'https://example.test/video'}
    monitor.totalTime = 1000
    monitor.playedTime = 899
    monitor._markProgress()
    assert store.contains(key) is False
    monitor.playedTime = 900
    monitor._markProgress()
    assert playbackstate.WatchedStore(store.path).contains(key) is True
    assert monitor.marked is True
    assert 'example.test' not in (tmp_path / 'watched.json').read_text()


def test_unknown_video_duration_is_not_marked_watched(tmp_path):
    store = playbackstate.WatchedStore(str(tmp_path / 'watched.json'))
    monitor = playbackstate.PlaybackMonitor(store)
    key = playbackstate.itemKey('source', 'Live')
    monitor.context = {'watch_id': key}
    monitor.totalTime = 0
    monitor.playedTime = 5000
    monitor._markProgress()
    assert store.contains(key) is False


def test_episode_watched_key_survives_title_and_queue_changes():
    assert playbackstate.itemKey('source', 'Episode 2', '01', '02', 'Series') == (
        playbackstate.itemKey('source', 'Other label', '1', '2', 'Series'))
    assert playbackstate.itemKey('source', 'Episode', '1', '2', 'Series') != (
        playbackstate.itemKey('source', 'Episode', '1', '3', 'Series'))


def test_playback_start_returns_without_waiting_for_video_end(monkeypatch):
    commands = []
    created = []

    class VideoPlayer:
        def __init__(self):
            self.streamFinished = False
            self.avStarted = False
            created.append(self)

    class Monitor:
        def abortRequested(self):
            return False

        def waitForAbort(self, timeout):
            assert timeout == 1
            created[0].avStarted = True

    monkeypatch.setattr(player, 'GerxstreamPlayer', VideoPlayer)
    monkeypatch.setattr(player.xbmc, 'Monitor', Monitor)
    monkeypatch.setattr(player.xbmc, 'executebuiltin', lambda *args: commands.append(args))

    assert player.cPlayer().startPlayer() is True
    assert commands == []


def test_playback_already_fullscreen_keeps_dialogs_open(monkeypatch):
    commands = []

    class VideoPlayer:
        streamFinished = False
        avStarted = True

    class Monitor:
        def abortRequested(self):
            return False

    monkeypatch.setattr(player, 'GerxstreamPlayer', VideoPlayer)
    monkeypatch.setattr(player.xbmc, 'Monitor', Monitor)
    monkeypatch.setattr(player.xbmc, 'executebuiltin', lambda *args: commands.append(args))

    assert player.cPlayer().startPlayer() is True
    assert commands == []


def test_playback_failure_does_not_open_fullscreen(monkeypatch):
    commands = []

    class VideoPlayer:
        streamFinished = True
        avStarted = False

    class Monitor:
        def abortRequested(self):
            return False

    monkeypatch.setattr(player, 'GerxstreamPlayer', VideoPlayer)
    monkeypatch.setattr(player.xbmc, 'Monitor', Monitor)
    monkeypatch.setattr(player.xbmc, 'executebuiltin', commands.append)

    assert player.cPlayer().startPlayer() is False
    assert commands == []


def test_av_started_switches_fullscreen_once_without_closing_dialogs(monkeypatch):
    commands = []
    monkeypatch.setattr(player.xbmc, 'getCondVisibility', lambda _condition: False)
    monkeypatch.setattr(player.xbmc, 'executebuiltin', lambda *args: commands.append(args))

    kodi_player = player.GerxstreamPlayer()
    kodi_player.onAVStarted()

    assert kodi_player.avStarted is True
    assert commands == [('ActivateWindow(FullScreenVideo)', True)]


def test_av_started_leaves_kodi_fullscreen_alone(monkeypatch):
    commands = []
    monkeypatch.setattr(player.xbmc, 'getCondVisibility', lambda _condition: True)
    monkeypatch.setattr(player.xbmc, 'executebuiltin', lambda *args: commands.append(args))

    player.GerxstreamPlayer().onAVStarted()

    assert commands == []


def test_old_player_stop_cannot_clear_a_new_episode_playlist(monkeypatch):
    import xbmcgui

    old_player = player.GerxstreamPlayer()
    window = xbmcgui.Window(10000)
    window.setProperty(player.EPISODE_PLAYLIST_PROPERTY, 'queue:0:current')
    new_player = player.GerxstreamPlayer()
    monkeypatch.setattr(player.cPlayer, '_activePlayer', new_player)

    old_player.onPlayBackStopped()

    assert window.getProperty(player.EPISODE_PLAYLIST_PROPERTY) == 'queue:0:current'
    new_player.onPlayBackStopped()
    assert window.getProperty(player.EPISODE_PLAYLIST_PROPERTY) == ''
