# -*- coding: utf-8 -*-
# Python 3

import xbmc
import xbmcgui
import time
from resources.lib.gui.gui import cGui
from resources.lib.config import cConfig
from xbmc import LOGINFO as LOGNOTICE, LOGERROR
from resources.lib.tools import addon_log as log
from resources.lib.episodequeue import EPISODE_PLAYLIST_PROPERTY


class GerxstreamPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        # super() statt unbound Base-Call: xbmc.Player.__init__(self, ...) wirft
        # unter Kodi 22 / Python 3.14 einen TypeError (xbmc/xbmc#29309).
        super().__init__(*args, **kwargs)
        self.streamFinished = False
        self.streamSuccess = True
        self.playedTime = 0
        self.totalTime = 999999
        self.avStarted = False
        self._episodeMarker = xbmcgui.Window(10000).getProperty(EPISODE_PLAYLIST_PROPERTY)
        log(cConfig().getLocalizedString(30166) + ' -> [player]: player instance created', LOGNOTICE)

    def onPlayBackStarted(self):
        log(cConfig().getLocalizedString(30166) + ' -> [player]: starting Playback', LOGNOTICE)
        self.totalTime = self.getTotalTime()

    def onPlayBackStopped(self):
        log(cConfig().getLocalizedString(30166) + ' -> [player]: Playback stopped', LOGNOTICE)
        if self.playedTime == 0 and self.totalTime == 999999:
            self.streamSuccess = False
            log(cConfig().getLocalizedString(30166) + ' -> [player]: Kodi failed to open stream', LOGERROR)
        self.streamFinished = True
        self._clearEpisodePlaylist()

    def onPlayBackEnded(self):
        log(cConfig().getLocalizedString(30166) + ' -> [player]: Playback completed', LOGNOTICE)
        # Kodi can emit this callback while it advances a native playlist.
        # Keep the marker until the last queued item has ended, otherwise the
        # next plugin:// item would be mistaken for a manual selection.
        self.streamFinished = True
        try:
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            if playlist.getposition() >= playlist.size() - 1:
                self._clearEpisodePlaylist()
        except Exception:
            self._clearEpisodePlaylist()

    def onPlayBackError(self):
        log(cConfig().getLocalizedString(30166) + ' -> [player]: Playback error', LOGERROR)
        self.streamSuccess = False
        self.streamFinished = True
        self._clearEpisodePlaylist()

    def onAVStarted(self):
        """Kodi has an audio/video decoder; only now may fullscreen be asked."""
        self.avStarted = True
        if not xbmc.getCondVisibility('Window.IsActive(FullScreenVideo)'):
            # Do not close dialogs or rebuild the renderer here.  Kodi has
            # already attached a decoder at this point, so a single window
            # activation avoids the MediaCodec InstanceGuard race.
            xbmc.executebuiltin('ActivateWindow(FullScreenVideo)', True)

    def _clearEpisodePlaylist(self):
        try:
            # A previous retained Player can receive its delayed stop callback
            # after a new manual playback has already registered its own
            # queue.  Only the currently active instance may clear the marker.
            if cPlayer._activePlayer is not self:
                return
            window = xbmcgui.Window(10000)
            if window.getProperty(EPISODE_PLAYLIST_PROPERTY) != self._episodeMarker:
                return
            window.clearProperty(EPISODE_PLAYLIST_PROPERTY)
            # Stop setzt auch den gemerkten Hoster zurueck: die naechste
            # manuell gestartete Folge fragt wieder ganz normal.
            from resources.lib import hosterprefs
            hosterprefs.forgetSticky()
            cPlayer._activePlayer = None
        except Exception:
            pass


class cPlayer:
    # Player callbacks are delivered to the Python instance.  Retain it after
    # the directory call returns so a user Stop can clear the episode marker.
    _activePlayer = None

    def clearPlayList(self):
        oPlaylist = self.__getPlayList()
        oPlaylist.clear()

    def __getPlayList(self):
        return xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

    def addItemToPlaylist(self, oGuiElement):
        oListItem = cGui().createListItem(oGuiElement)
        self.__addItemToPlaylist(oGuiElement, oListItem)

    def __addItemToPlaylist(self, oGuiElement, oListItem):
        oPlaylist = self.__getPlayList()
        oPlaylist.add(oGuiElement.getMediaUrl(), oListItem)

    def startPlayer(self):
        log(cConfig().getLocalizedString(30166) + ' -> [player]: start player', LOGNOTICE)
        xbmcPlayer = GerxstreamPlayer()
        self.__class__._activePlayer = xbmcPlayer
        monitor = xbmc.Monitor()
        startTime = time.time()
        while not monitor.abortRequested():
            if xbmcPlayer.avStarted:
                # Die Plugin-Aktion muss nach dem Decoderstart zurueckkehren.
                # ``onAVStarted`` hat den Vollbildwechsel bei Bedarf bereits
                # ausgefuehrt, ohne Kodi zu einem vorzeitigen Renderer-Neuaufbau
                # zu zwingen.
                return True
            if xbmcPlayer.streamFinished:
                return False
            if (time.time() - startTime) >= 60:
                log(cConfig().getLocalizedString(30166) + ' -> [player]: Playback start timeout after 60s', LOGERROR)
                return False
            monitor.waitForAbort(1)
        return False
