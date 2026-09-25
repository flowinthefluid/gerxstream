# -*- coding: utf-8 -*-
"""The plugin must wait for the decoder callback before completing playback."""

from resources.lib import player


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
    new_player = player.GerxstreamPlayer()
    window = xbmcgui.Window(10000)
    window.setProperty(player.EPISODE_PLAYLIST_PROPERTY, 'queue:0:current')
    monkeypatch.setattr(player.cPlayer, '_activePlayer', new_player)

    old_player.onPlayBackStopped()

    assert window.getProperty(player.EPISODE_PLAYLIST_PROPERTY) == 'queue:0:current'
    new_player.onPlayBackStopped()
    assert window.getProperty(player.EPISODE_PLAYLIST_PROPERTY) == ''
