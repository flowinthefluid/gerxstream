# -*- coding: utf-8 -*-
# Python 3

from xbmc import LOGINFO as LOGNOTICE
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import addon_log as log

class cJDownloaderHandler:
    def sendToJDownloader(self, sUrl):
        if self.__checkConfig() == False:
            cGui().showError(cConfig().getLocalizedString(30070), cConfig().getLocalizedString(30254), 5)
            return False

        if self.__checkConnection() == False:
            cGui().showError(cConfig().getLocalizedString(30070), cConfig().getLocalizedString(30255), 5)
            return False

        bDownload = self.__download(sUrl)
        if bDownload == True:
            cGui().showInfo(cConfig().getLocalizedString(30070), cConfig().getLocalizedString(30256), 5)

    def __checkConfig(self):
        log(cConfig().getLocalizedString(30166) + ' -> [jdownloaderHandler]: check JD Addon settings', LOGNOTICE)
        
        return cConfig().getSettingBool('jd_enabled')

    def __getHost(self):
        return cConfig().getSetting('jd_host')

    def __getPort(self):
        return cConfig().getSettingInt('jd_port', 10025)

    def __getAutomaticStart(self):
        # Hinweis: jd_automatic_start ist in resources/settings.xml nicht
        # definiert, der Wert ist daher immer der Default False. Verhalten
        # unveraendert uebernommen, siehe N1.
        return cConfig().getSettingBool('jd_automatic_start')

    def __getLinkGrabber(self):
        # Hinweis: jd_grabber ist in resources/settings.xml ebenfalls nicht
        # definiert, siehe __getAutomaticStart().
        return cConfig().getSettingBool('jd_grabber')

    def __download(self, sFileUrl):
        sHost = self.__getHost()
        sPort = self.__getPort()
        bAutomaticDownload = self.__getAutomaticStart()
        bLinkGrabber = self.__getLinkGrabber()
        sLinkForJd = self.__createJDUrl(sFileUrl, sHost, sPort, bAutomaticDownload, bLinkGrabber)
        log(cConfig().getLocalizedString(30166) + ' -> [jdownloaderHandler]: JD Link: ' + str(sLinkForJd), LOGNOTICE)
        oRequestHandler = cRequestHandler(sLinkForJd)
        oRequestHandler.request()
        return True

    def __createJDUrl(self, sFileUrl, sHost, sPort, bAutomaticDownload, bLinkGrabber):
        sGrabber = '0'
        if bLinkGrabber == True:
            sGrabber = '1'
        sAutomaticStart = '0'
        if bAutomaticDownload == True:
            sAutomaticStart = '1'
        sUrl = 'http://' + str(sHost) + ':' + str(sPort) + '/action/add/links/grabber' + str(sGrabber) + '/start' + str(
            sAutomaticStart) + '/' + sFileUrl
        return sUrl

    def __checkConnection(self):
        log(cConfig().getLocalizedString(30166) + ' -> [jdownloaderHandler]: check JD Connection', LOGNOTICE)
        sHost = self.__getHost()
        sPort = self.__getPort()
        sLinkForJd = 'http://' + str(sHost) + ':' + str(sPort)
        try:
            oRequestHandler = cRequestHandler(sLinkForJd)
            oRequestHandler.request()
            return True
        except Exception as e:
            return False
        return False
