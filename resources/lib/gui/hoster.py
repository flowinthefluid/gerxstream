# -*- coding: utf-8 -*-
# Python 3
#
# 24.01.23 - Heptamer: Korrektur getpriorities (nun werden alle Hoster gelesen und sortiert)
# 22.12.24 - Heptamer: m3u8 und mpd Files über inputstream adaptive abspielen lassen

import xbmc
import xbmcgui
import xbmcplugin
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.gui.gui import cGui
from resources.lib.config import cConfig
from resources.lib.player import cPlayer, EPISODE_PLAYLIST_PROPERTY
from resources.lib.tools import logger


class cHosterGui:
    SITE_NAME = 'cHosterGui'
    EPISODE_PLAYLIST_PROPERTY = EPISODE_PLAYLIST_PROPERTY

    def __init__(self):
        self.maxHoster = cConfig().getSettingInt('maxHoster', 100)
        self.dialog = False

    # TODO: unify parts of play, download etc.
    def _getInfoAndResolve(self, siteResult):
        oGui = cGui()
        params = ParameterHandler()
        # get data
        mediaUrl = params.getValue('sMediaUrl')
        fileName = params.getValue('MovieTitle')
        try:
            try:
                import resolveurl as resolver
            except Exception:
                import urlresolver as resolver
            # resolve
            if siteResult:
                mediaUrl = siteResult.get('streamUrl', False)
                mediaId = siteResult.get('streamID', False)
                if mediaUrl:
                    logger.info('-> [hoster]: resolve: ' + cRequestHandler._safeUrlForLog(mediaUrl))
                    link = mediaUrl if siteResult['resolved'] else resolver.resolve(mediaUrl)
                elif mediaId:
                    logger.info('-> [hoster]: resolve: hoster: %s - mediaID: %s' % (siteResult['host'], mediaId))
                    link = resolver.HostedMediaFile(host=siteResult['host'].lower(), media_id=mediaId).resolve()
                else:
                    oGui.showError('GerXStream', cConfig().getLocalizedString(30134), 5)
                    return False
            elif mediaUrl:
                logger.info('-> [hoster]: resolve: ' + cRequestHandler._safeUrlForLog(mediaUrl))
                link = resolver.resolve(mediaUrl)
            else:
                oGui.showError('GerXStream', cConfig().getLocalizedString(30134), 5)
                return False
        except resolver.resolver.ResolverError as e:
            logger.error('-> [hoster]: ResolverError: %s' % e)
            oGui.showError('GerXStream', cConfig().getLocalizedString(30135), 7)
            return False
        except Exception as e:
            # A deleted hoster item can surface as urllib HTTPError inside
            # ResolveURL.  It is not an add-on crash and must not leave Kodi
            # with a full traceback (nor log a possibly signed source URL).
            logger.error('-> [hoster]: resolver failed (%s)' % type(e).__name__)
            oGui.showError('GerXStream', cConfig().getLocalizedString(30135), 7)
            return False
        # resolver response
        if link is not False:
            data = {'title': fileName, 'season': params.getValue('season'), 'episode': params.getValue('episode'), 'showTitle': params.getValue('TVShowTitle'), 'thumb': params.getValue('thumb'), 'link': link}
            return data
        return False

    @classmethod
    def _playlistState(cls):
        """Return the queue id and first index of a native episode playlist."""
        value = xbmcgui.Window(10000).getProperty(cls.EPISODE_PLAYLIST_PROPERTY)
        try:
            # The nonce intentionally invalidates the two-field marker used by
            # older releases.  Such a marker may have survived a stopped
            # playback and must never turn a manual selection into a queued
            # item after an add-on update.
            queueId, firstIndex, nonce = value.split(':', 2)
            if not nonce:
                raise ValueError
            return queueId, int(firstIndex)
        except (AttributeError, TypeError, ValueError):
            if value:
                xbmcgui.Window(10000).clearProperty(cls.EPISODE_PLAYLIST_PROPERTY)
            return '', -1

    @classmethod
    def _isNativeEpisodePlaylistItem(cls, params):
        """Whether Kodi is resolving a later item of our active playlist."""
        queueId, firstIndex = cls._playlistState()
        try:
            index = int(params.getValue('episodeIndex'))
        except (TypeError, ValueError):
            return False
        if not queueId or queueId != params.getValue('episodeQueue') or index <= firstIndex:
            return False
        try:
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            position = playlist.getposition()
        except Exception:
            return False
        # ``episodeIndex`` belongs to the complete directory; the native
        # playlist starts with the manually selected item at position zero.
        # Matching the exact relative position rejects a stale playlist marker
        # after Stop + a new manual episode selection.
        return bool(position == index - firstIndex
                    and position > 0
                    and playlist.size() > position)

    @classmethod
    def _queueFollowingEpisodes(cls, params):
        """Append later episodes to Kodi's already playing video playlist.

        Kodi resolves the later ``plugin://`` entries itself. Consequently its
        regular "next item" remote action works as well as natural automatic
        advancement; no direct hoster URLs are stored in the episode queue.
        The selected episode is already in Kodi's playlist. Replacing and
        playing that playlist again would restart the same video.
        """
        if not cConfig().getSettingBool('autoNextEpisodeEnabled', False):
            return False
        try:
            firstIndex = int(params.getValue('episodeIndex'))
        except (TypeError, ValueError):
            return False
        queueId = params.getValue('episodeQueue')
        from resources.lib import episodequeue
        targets = episodequeue.getTargets(queueId)
        if firstIndex < 0 or firstIndex >= len(targets) - 1:
            return False

        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        if playlist.size() != 1 or playlist.getposition() != 0:
            return False
        for target in targets[firstIndex + 1:]:
            queuedItem = xbmcgui.ListItem(path=target)
            queuedItem.setProperty('IsPlayable', 'true')
            # Kodi >= 20 otherwise may reuse an old resolver result if the
            # same episode is played again from this playlist.
            queuedItem.setProperty('ForceResolvePlugin', 'true')
            playlist.add(target, queuedItem)
        # The nonce distinguishes this live queue from legacy markers which
        # had no reliable lifecycle on Kodi stop events.
        import uuid
        xbmcgui.Window(10000).setProperty(cls.EPISODE_PLAYLIST_PROPERTY,
                                          '%s:%d:%s' % (queueId, firstIndex,
                                                        uuid.uuid4().hex))
        return True

    @classmethod
    def _finishNativeEpisodePlaylist(cls, params):
        """Forget the marker after Kodi asks the add-on to resolve its last item."""
        try:
            index = int(params.getValue('episodeIndex'))
        except (TypeError, ValueError):
            return
        from resources.lib import episodequeue
        targets = episodequeue.getTargets(params.getValue('episodeQueue'))
        if targets and index >= len(targets) - 1:
            xbmcgui.Window(10000).clearProperty(cls.EPISODE_PLAYLIST_PROPERTY)

    def play(self, siteResult=False):
        logger.info('-> [hoster]: attempt to play file')
        data = self._getInfoAndResolve(siteResult)
        if not data:
            return False
        if self.dialog:
            try:
                self.dialog.close()
            except Exception:
                pass

        vers = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
        stream_url = (siteResult or {}).get('streamUrl', '')

        logger.info('-> [hoster]: play file link: ' + cRequestHandler._safeUrlForLog(data['link']))
        list_item = xbmcgui.ListItem(path=data['link'])
        #m3u8 und mpd via inputstream, exklusive Filemoon, da IA mit dem Hoster nicht unter Android läuft
        if 'filemoon' not in stream_url:
            if '.m3u8' in data['link'] or '.mpd' in data['link']:
                list_item.setProperty("inputstream", "inputstream.adaptive")
                if '.mpd' in data['link']:
                    if vers < 21: list_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
                    list_item.setMimeType('application/dash+xml')
                else:
                    if vers < 21: list_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                    list_item.setMimeType("application/vnd.apple.mpegurl")
                if '|' in data['link']:
                    data['link'], header = data['link'].split('|')
                    list_item.setProperty('inputstream.adaptive.stream_headers', header)
                    if vers > 19: list_item.setProperty('inputstream.adaptive.manifest_headers', header)

        if 'youtube' in data['link']:
            import time
            time.sleep(1)
        info = {'Title': data['title']}
        if data['thumb']:
            list_item.setArt({'thumb': data['thumb'], 'poster': data['thumb']})
        if data['showTitle']:
            info['Episode'] = data['episode']
            info['Season'] = data['season']
            info['TVShowTitle'] = data['showTitle']

        vtag = list_item.getVideoInfoTag()
        vtag.setMediaType('video')
        if 'Title' in info:
            try:
                vtag.setTitle(str(info['Title']))
            except: pass
        if 'Season' in info:
            try:
                vtag.setSeason(int(info['Season']))
            except: pass
        if 'Episode' in info:
            try:
                vtag.setEpisode(int(info['Episode']))
            except: pass
        if 'TVShowTitle' in info:
            try:
                vtag.setTvShowTitle(info['TVShowTitle'])
            except: pass

        list_item.setProperty('IsPlayable', 'true')
        params = ParameterHandler()
        # The following entries of a real Kodi playlist are invoked by Kodi
        # only to obtain their resolved stream. They must return immediately;
        # waiting for their playback would block the playlist transition.
        if self._isNativeEpisodePlaylistItem(params):
            if cGui().pluginHandle > 0:
                xbmcplugin.setResolvedUrl(cGui().pluginHandle, True, list_item)
            else:
                xbmc.Player().play(data['link'], list_item)
            self._finishNativeEpisodePlaylist(params)
            return True

        pluginHandle = cGui().pluginHandle
        if pluginHandle > 0:
            self._queueFollowingEpisodes(params)
            # Kodi is already opening this playable item. Resolving it is the
            # sole playback start; future episodes were added to its playlist.
            xbmcplugin.setResolvedUrl(pluginHandle, True, list_item)
        else:
            xbmc.Player().play(data['link'], list_item)
        player = cPlayer()
        started = player.startPlayer()
        if started:
            # Erst nach erfolgreichem Start erfassen; Links und Hoster werden
            # bewusst nicht gespeichert, nur die lokal sichtbaren Metadaten.
            try:
                from resources.lib import history
                history.record(data['title'], data.get('thumb', ''),
                               params.getValue('mediaType') or 'movie',
                               params.getValue('site'), params.getValue('season'),
                               params.getValue('episode'), data.get('showTitle', ''))
            except Exception:
                logger.error('-> [hoster]: could not store playback history')
        return started

    def addToPlaylist(self, siteResult=False):
        oGui = cGui()
        logger.info('-> [hoster]: attempt addToPlaylist')
        data = self._getInfoAndResolve(siteResult)
        if not data: return False
        logger.info('-> [hoster]: addToPlaylist file link: ' + cRequestHandler._safeUrlForLog(data['link']))
        oGuiElement = cGuiElement()
        oGuiElement.setSiteName(self.SITE_NAME)
        oGuiElement.setMediaUrl(data['link'])
        oGuiElement.setTitle(data['title'])
        if data['thumb']:
            oGuiElement.setThumbnail(data['thumb'])
        if data['showTitle']:
            oGuiElement.setEpisode(data['episode'])
            oGuiElement.setSeason(data['season'])
            oGuiElement.setTVShowTitle(data['showTitle'])
        if self.dialog:
            self.dialog.close()
        oPlayer = cPlayer()
        oPlayer.addItemToPlaylist(oGuiElement)
        oGui.showInfo(cConfig().getLocalizedString(30136), cConfig().getLocalizedString(30137), 5)
        return True

    def download(self, siteResult=False):
        from resources.lib.download import cDownload
        logger.info('-> [hoster]: attempt download')
        data = self._getInfoAndResolve(siteResult)
        if not data: return False
        logger.info('-> [hoster]: download file link: ' + data['link'])
        if self.dialog:
            self.dialog.close()
        oDownload = cDownload()
        oDownload.download(data['link'], data['title'])
        return True

    def sendToPyLoad(self, siteResult=False):
        from resources.lib.handler.pyLoadHandler import cPyLoadHandler
        logger.info('-> [hoster]: attempt download with pyLoad')
        data = self._getInfoAndResolve(siteResult)
        if not data: return False
        cPyLoadHandler().sendToPyLoad(data['title'], data['link'])
        return True

    def sendToJDownloader(self, sMediaUrl=False):
        from resources.lib.handler.jdownloaderHandler import cJDownloaderHandler
        params = ParameterHandler()
        if not sMediaUrl:
            sMediaUrl = params.getValue('sMediaUrl')
        if self.dialog:
            self.dialog.close()
        logger.info('-> [hoster]: call send to JDownloader: ' + sMediaUrl)
        cJDownloaderHandler().sendToJDownloader(sMediaUrl)

    def sendToJDownloader2(self, sMediaUrl=False):
        from resources.lib.handler.jdownloader2Handler import cJDownloader2Handler
        params = ParameterHandler()
        if not sMediaUrl:
            sMediaUrl = params.getValue('sMediaUrl')
        if self.dialog:
            self.dialog.close()
        logger.info('-> [hoster]: call send to JDownloader2: ' + sMediaUrl)
        cJDownloader2Handler().sendToJDownloader2(sMediaUrl)

    def sendToMyJDownloader(self, sMediaUrl=False, sMovieTitle='GerXStream'):
        from resources.lib.handler.myjdownloaderHandler import cMyJDownloaderHandler
        params = ParameterHandler()
        if not sMediaUrl:
            sMediaUrl = params.getValue('sMediaUrl')
        sMovieTitle = params.getValue('MovieTitle')
        if not sMovieTitle:
            sMovieTitle = params.getValue('Title')
        if not sMovieTitle:  # only temporary
            sMovieTitle = params.getValue('sMovieTitle')
        if not sMovieTitle:
            sMovieTitle = params.getValue('title')
        if self.dialog:
            self.dialog.close()
        logger.info('-> [hoster]: call send to My.JDownloader: ' + sMediaUrl)
        cMyJDownloaderHandler().sendToMyJDownloader(sMediaUrl, sMovieTitle)

    def __getPriorities(self, hosterList, filter=True):
        # Sort hosters based on their resolvers priority.
        ranking = []
        # handles multihosters but is about 10 times slower
        for hoster in hosterList:

            # we try to load resolveurl within the loop, making sure that the resolver loads new with every cycle
            try:
                import resolveurl as resolver
            except Exception:
                import urlresolver as resolver

            # accept hoster which is marked as resolveable by sitePlugin
            if hoster.get('resolveable', False):
                ranking.append([0, hoster])
                continue

            try:
                # serienstream VOE hoster = {'link': [sUrl, sName], aus array "[0]" True bzw. False
                link = hoster['link'][0] if isinstance(hoster['link'], list) else hoster['link']
                hmf = resolver.HostedMediaFile(url=link)
                #hmf = resolver.HostedMediaFile(url=hoster['link'])
            except Exception:
                continue

            if not hmf.valid_url():
                hmf = resolver.HostedMediaFile(host=hoster['name'].lower(), media_id='dummy')

            if len(hmf.get_resolvers()):
                priority = False
                for resolver_instance in hmf.get_resolvers():
                    # prefer individual priority
                    if not resolver_instance.isUniversal():
                        priority = resolver_instance._get_priority()
                        break
                    if not priority:
                        priority = resolver_instance._get_priority()
                if priority:
                    ranking.append([priority, hoster])
            elif not filter:
                ranking.append([999, hoster])

        if any('quality' in hoster[1] for hoster in ranking):
            try:
                # Sortiere Hoster nach Qualität (cConfig().getSetting('preferedQuality') == '5')
                pref_quali = cConfig().getSetting('preferedQuality')
                if pref_quali != '5' and any('quality' in hoster[1] and int(hoster[1]['quality']) == int(pref_quali) for hoster in ranking):
                    ranking = sorted(ranking, key=lambda hoster: int('quality' in hoster[1] and hoster[1]['quality']) == int(pref_quali), reverse=True)
                else:
                # Wenn Hosterliste prüfen an ist, sortiere Hoster nach Prio Qualität
                    ranking = sorted(ranking, key=lambda hoster: 'quality' in hoster[1] and int(hoster[1]['quality']), reverse=True)
            except Exception:
                pass
        # After sorting Quality, we sort for Hoster-Priority :) -Hep 24.01.23
        # ranking = sorted(ranking, key=lambda ranking: ranking[0])

        # Hoster Sprache über sLang im Siteplugin Prio nach sLang Code Reihenfolge (Deutsch, Englisch, Englisch mit untertitel
        if ranking:
            if  "languageCode" in ranking[0][1]:
                ranking = sorted(ranking, key=lambda ranking: (ranking[1]["languageCode"],ranking[0]))
            else:
                ranking = sorted(ranking, key=lambda ranking: ranking[0])


        hosterQueue = []

        for i, hoster in ranking:
            hosterQueue.append(hoster)
        return hosterQueue

    def stream(self, playMode, siteName, function, url):
        self.dialog = xbmcgui.DialogProgress()
        try:
            self.dialog.create('GerXStream', cConfig().getLocalizedString(30138))
            # load site as plugin and run the function
            self.dialog.update(5, cConfig().getLocalizedString(30139))
            plugin = __import__(siteName, globals(), locals())
            function = getattr(plugin, function)
            self.dialog.update(10, cConfig().getLocalizedString(30140))
            if url:
                siteResult = function(url)
            else:
                siteResult = function()
            self.dialog.update(40)
            if not siteResult:
                cGui().showInfo('GerXStream', cConfig().getLocalizedString(30141))
                return
            # if result is not a list, make in one
            if not type(siteResult) is list:
                temp = [siteResult]
                siteResult = temp
            if not siteResult or not isinstance(siteResult[0], dict):
                cGui().showInfo('GerXStream', cConfig().getLocalizedString(30141))
                return
            # field "name" marks hosters
            if 'name' in siteResult[0]:
                functionName = siteResult[-1]
                del siteResult[-1]
                if not siteResult:
                    cGui().showInfo('GerXStream', cConfig().getLocalizedString(30142))
                    return

                self.dialog.update(60, cConfig().getLocalizedString(30143))
                # Sitplugins VOD mit in automatische Abspielliste aufnehmen (Da Links bei der Überprüfung der Verfügbarkeit gekickt werden)
                if (playMode != 'jd') and (playMode != 'jd2') and (playMode != 'pyload') and cConfig().getSettingBool('presortHoster', False) and (playMode != 'myjd'):
                #if (not siteName.startswith('vod_')) and (playMode != 'jd') and (playMode != 'jd2') and (playMode != 'pyload') and (cConfig().getSetting('presortHoster') == 'true') and (playMode != 'myjd'):
                    siteResult = self.__getPriorities(siteResult)
                if not siteResult:
                    cGui().showInfo('GerXStream', cConfig().getLocalizedString(30144))
                    return False
                self.dialog.update(90)
                if len(siteResult) > self.maxHoster:
                    siteResult = siteResult[:self.maxHoster - 1]
                if cConfig().getSetting('hosterSelect') == 'List':
                    self.showHosterFolder(siteResult, siteName, functionName)
                    return
                if len(siteResult) > 1:
                    # choose hoster
                    siteResult = self._chooseHoster(siteResult)
                    if not siteResult:
                        return
                else:
                    siteResult = siteResult[0]
                # get stream links
                logger.info(siteResult['link'])
                function = getattr(plugin, functionName)
                siteResult = function(siteResult['link'])
                # if result is not a list, make in one
                if not type(siteResult) is list:
                    temp = [siteResult]
                    siteResult = temp
                if not siteResult or not isinstance(siteResult[0], dict):
                    cGui().showInfo('GerXStream', cConfig().getLocalizedString(30141))
                    return
            # choose part
            if len(siteResult) > 1:
                siteResult = self._choosePart(siteResult)
                if not siteResult:
                    logger.info('-> [hoster]: no part selected')
                    return
            else:
                siteResult = siteResult[0]

            self.dialog.create('GerXStream', cConfig().getLocalizedString(30145))
            self.dialog.update(95, cConfig().getLocalizedString(30146))
            if playMode == 'play':
                self.play(siteResult)
            elif playMode == 'download':
                self.download(siteResult)
            elif playMode == 'enqueue':
                self.addToPlaylist(siteResult)
            elif playMode == 'jd':
                self.sendToJDownloader(siteResult['streamUrl'])
            elif playMode == 'jd2':
                self.sendToJDownloader2(siteResult['streamUrl'])
            elif playMode == 'myjd':
                self.sendToMyJDownloader(siteResult['streamUrl'])
            elif playMode == 'pyload':
                self.sendToPyLoad(siteResult)
        finally:
            try:
                self.dialog.close()
            except Exception:
                pass

    def streamAuto(self, playMode, siteName, function):
        logger.info('-> [hoster]: auto stream initiated')
        self.dialog = xbmcgui.DialogProgress()
        self.dialog.create('GerXStream', cConfig().getLocalizedString(30138))
        # load site as plugin and run the function
        self.dialog.update(5, cConfig().getLocalizedString(30139))
        plugin = __import__(siteName, globals(), locals())
        function = getattr(plugin, function)
        self.dialog.update(10, cConfig().getLocalizedString(30140))
        siteResult = function()
        if not siteResult:
            self.dialog.close()
            cGui().showInfo('GerXStream', cConfig().getLocalizedString(30141))
            return False
        # if result is not a list, make in one
        if not type(siteResult) is list:
            temp = [siteResult]
            siteResult = temp
        if not siteResult or not isinstance(siteResult[0], dict):
            self.dialog.close()
            cGui().showInfo('GerXStream', cConfig().getLocalizedString(30141))
            return False
        # field "name" marks hosters
        if 'name' in siteResult[0]:
            self.dialog.update(90, cConfig().getLocalizedString(30143))
            functionName = siteResult[-1]
            del siteResult[-1]
            # Sitplugins aus dem VOD Bereich bei self.__getPriorities(siteResult) ausschliessen da sonst die Hoster gekickt werden.
            if siteName.startswith('dummy'): #Falls Servernamen im VOD sich ändern, hier vod_ eintragen
                hosters = siteResult
            else:
                hosters = self.__getPriorities(siteResult)
            if not hosters:
                self.dialog.close()
                cGui().showInfo('GerXStream', cConfig().getLocalizedString(30144))
                return False
            if len(siteResult) > self.maxHoster:
                siteResult = siteResult[:self.maxHoster - 1]
            check = False
            self.dialog.create('GerXStream', cConfig().getLocalizedString(30147))
            total = len(hosters)
            for count, hoster in enumerate(hosters):
                if self.dialog.iscanceled() or xbmc.Monitor().abortRequested() or check: return
                percent = (count + 1) * 100 // total
                try:
                    logger.info('-> [hoster]: try hoster %s' % hoster['name'])
                    self.dialog.create('GerXStream', cConfig().getLocalizedString(30147))
                    self.dialog.update(percent, cConfig().getLocalizedString(30147) + ' %s' % hoster['name'])
                    # get stream links
                    function = getattr(plugin, functionName)
                    siteResult = function(hoster['link'])
                    check = self.__autoEnqueue(siteResult, playMode)
                    if check:
                        return True
                except Exception:
                    self.dialog.update(percent, cConfig().getLocalizedString(30148) % hoster['name'])
                    logger.error('-> [hoster]: playback with hoster %s failed' % hoster['name'])
        # field "resolved" marks streamlinks
        elif 'resolved' in siteResult[0]:
            for stream in siteResult:
                try:
                    if self.__autoEnqueue(siteResult, playMode):
                        self.dialog.close()
                        return True
                except Exception:
                    pass

    def _chooseHoster(self, siteResult):
        dialog = xbmcgui.Dialog()
        titles = []
        for result in siteResult:
            if 'displayedName' in result:
                titles.append(str(result['displayedName']))
            else:
                titles.append(str(result['name']))
        index = dialog.select(cConfig().getLocalizedString(30149), titles)
        if index > -1:
            siteResult = siteResult[index]
            return siteResult
        else:
            logger.info('-> [hoster]: no hoster selected')
            return False

    def _choosePart(self, siteResult):
        self.dialog = xbmcgui.Dialog()
        titles = []
        for result in siteResult:
            titles.append(str(result['title']))
        index = self.dialog.select(cConfig().getLocalizedString(30150), titles)
        if index > -1:
            siteResult = siteResult[index]
            return siteResult
        else:
            return False

    def showHosterFolder(self, siteResult, siteName, functionName):
        oGui = cGui()
        total = len(siteResult)
        params = ParameterHandler()
        for hoster in siteResult:
            if 'displayedName' in hoster:
                name = hoster['displayedName']
            else:
                name = hoster['name']
            oGuiElement = cGuiElement(name, siteName, functionName)
            oGuiElement.setThumbnail(str(params.getValue('thumb')))
            params.setParam('url', hoster['link'])
            params.setParam('isHoster', 'true')
            oGui.addFolder(oGuiElement, params, iTotal=total, isHoster=True)
        oGui.setEndOfDirectory()

    def __autoEnqueue(self, partList, playMode):
        # choose part
        if not partList:
            return False
        for i in range(len(partList) - 1, -1, -1):
            try:
                if playMode == 'play' and i == 0:
                    if not self.play(partList[i]):
                        return False
                elif playMode == 'download':
                    self.download(partList[i])
                elif playMode == 'enqueue' or (playMode == 'play' and i > 0):
                    self.addToPlaylist(partList[i])
            except Exception:
                return False
        logger.info('-> [hoster]: autoEnqueue successful')
        return True


class Hoster:
    def __init__(self, name, link):
        self.name = name
        self.link = link
