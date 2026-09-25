# -*- coding: utf-8 -*-
# Python 3

import xbmc
import time
from resources.lib.gui.gui import cGui
from resources.lib.config import cConfig
from xbmc import LOGINFO as LOGNOTICE, LOGERROR
from resources.lib.tools import addon_log as log

class GerxstreamPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        # super() statt unbound Base-Call: xbmc.Player.__init__(self, ...) wirft
        # unter Kodi 22 / Python 3.14 einen TypeError (xbmc/xbmc#29309).
        super().__init__(*args, **kwargs)
        self.streamFinished = False
        self.streamSuccess = True
        self.playedTime = 0
        self.totalTime = 999999
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

    def onPlayBackEnded(self):
        log(cConfig().getLocalizedString(30166) + ' -> [player]: Playback completed', LOGNOTICE)
        self.onPlayBackStopped()

    def onPlayBackError(self):
        log(cConfig().getLocalizedString(30166) + ' -> [player]: Playback error', LOGERROR)
        self.streamSuccess = False
        self.streamFinished = True


class cPlayer:
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
        monitor = xbmc.Monitor()
        startTime = time.time()
        while not monitor.abortRequested():
            if xbmcPlayer.isPlayingVideo():
                # Die Plugin-Aktion muss nach dem Start zurueckkehren. Sonst
                # bleibt die Episodenliste waehrend der Wiedergabe aktiv.
                if not xbmc.getCondVisibility('Window.IsActive(FullScreenVideo)'):
                    # Kodi verweigert ActivateWindow, solange ein modaler
                    # Dialog (z.B. vom Aufloesen des Streams) aktiv ist.
                    # Beide Befehle synchron ausfuehren, bevor die Aktion
                    # zur Episodenliste zurueckkehrt.
                    xbmc.executebuiltin('Dialog.Close(all,true)', True)
                    xbmc.executebuiltin('ActivateWindow(FullScreenVideo)', True)
                return True
            if xbmcPlayer.streamFinished:
                return False
            if (time.time() - startTime) >= 60:
                log(cConfig().getLocalizedString(30166) + ' -> [player]: Playback start timeout after 60s', LOGERROR)
                return False
            monitor.waitForAbort(1)
        return False
