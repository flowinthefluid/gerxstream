# -*- coding: utf-8 -*-
"""The plugin must release its playback call when Kodi starts the video."""

from resources.lib import player


def test_playback_start_returns_without_waiting_for_video_end(monkeypatch):
    checks = iter((False, True))
    commands = []

    class VideoPlayer:
        streamFinished = False

        def isPlayingVideo(self):
            return next(checks)

    class Monitor:
        def abortRequested(self):
            return False

        def waitForAbort(self, timeout):
            assert timeout == 1

    monkeypatch.setattr(player, 'GerxstreamPlayer', VideoPlayer)
    monkeypatch.setattr(player.xbmc, 'Monitor', Monitor)
    monkeypatch.setattr(player.xbmc, 'getCondVisibility', lambda condition: False)
    monkeypatch.setattr(player.xbmc, 'executebuiltin', lambda *args: commands.append(args))

    assert player.cPlayer().startPlayer() is True
    assert commands == [
        ('Dialog.Close(all,true)', True),
        ('ActivateWindow(FullScreenVideo)', True),
    ]


def test_playback_already_fullscreen_keeps_dialogs_open(monkeypatch):
    commands = []

    class VideoPlayer:
        streamFinished = False

        def isPlayingVideo(self):
            return True

    class Monitor:
        def abortRequested(self):
            return False

    monkeypatch.setattr(player, 'GerxstreamPlayer', VideoPlayer)
    monkeypatch.setattr(player.xbmc, 'Monitor', Monitor)
    monkeypatch.setattr(player.xbmc, 'getCondVisibility', lambda condition: True)
    monkeypatch.setattr(player.xbmc, 'executebuiltin', lambda *args: commands.append(args))

    assert player.cPlayer().startPlayer() is True
    assert commands == []


def test_playback_failure_does_not_open_fullscreen(monkeypatch):
    commands = []

    class VideoPlayer:
        streamFinished = True

        def isPlayingVideo(self):
            return False

    class Monitor:
        def abortRequested(self):
            return False

    monkeypatch.setattr(player, 'GerxstreamPlayer', VideoPlayer)
    monkeypatch.setattr(player.xbmc, 'Monitor', Monitor)
    monkeypatch.setattr(player.xbmc, 'executebuiltin', commands.append)

    assert player.cPlayer().startPlayer() is False
    assert commands == []
