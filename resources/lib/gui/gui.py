# -*- coding: utf-8 -*-
# Python 3

import sys
import uuid
import xbmc
import xbmcgui
import xbmcplugin

from resources.lib import utils, playbackstate
from resources.lib.config import cConfig
from resources.lib.gui.contextElement import cContextElement
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler
from urllib.parse import quote_plus, urlencode, parse_qsl, urlsplit, urlunsplit


class cGui:
    # Einige aeltere Quellen erzeugen fuer jeden Listeneintrag ein neues
    # cGui-Objekt. Die Queue muss deshalb pro Kodi-Verzeichnis geteilt und
    # nicht nur an einer einzelnen Instanz haengen.
    _episodeQueues = {}

    # This class "abstracts" a list of xbmc listitems.
    def __init__(self):
        try:
            self.pluginHandle = int(sys.argv[1])
        except Exception:
            self.pluginHandle = 0
        try:
            self.pluginPath = sys.argv[0]
        except Exception:
            self.pluginPath = ''
        self.isMetaOn = cConfig().getSettingBool('TMDBMETA', False)
        if cConfig().getSettingBool('metaOverwrite', False):
            self.metaMode = 'replace'
        else:
            self.metaMode = 'add'
        # for globalSearch or alterSearch
        self.globalSearch = False
        self._collectMode = False
        self._isViewSet = False
        self.searchResults = []
        self._episodeQueueKey = '%s|%s|%s' % (self.pluginPath, self.pluginHandle,
                                               sys.argv[2] if len(sys.argv) > 2 else '')

    def addFolder(self, oGuiElement, params='', bIsFolder=True, iTotal=0, isHoster=False):
        # add GuiElement to Gui, adds listitem to a list
        # store result in list if we searched global for other sources
        # Global-search providers run in background threads. Calling Kodi's
        # Monitor or directory APIs from there can block the entire plugin.
        # They only need to collect plain Python data at this point.
        if self._collectMode:
            import copy
            self.searchResults.append({'guiElement': oGuiElement, 'params': copy.deepcopy(params), 'isFolder': bIsFolder})
            return
        if params == '':
            params = ParameterHandler()
        # abort xbmc list creation if user requests abort
        if xbmc.Monitor().abortRequested():
            self.setEndOfDirectory(False)
            raise RuntimeError('UserAborted')
        if not oGuiElement._isMetaSet and self.isMetaOn and oGuiElement._mediaType and iTotal < 100:
            tmdbID = params.getValue('tmdbID')
            if tmdbID:
                oGuiElement.getMeta(oGuiElement._mediaType, tmdbID, mode=self.metaMode)
            else:
                oGuiElement.getMeta(oGuiElement._mediaType, mode=self.metaMode)
        # Jede normale Episodenliste erhaelt eine kurzlebige Kennung. Die
        # Liste selbst wird erst bei setEndOfDirectory gespeichert, wenn alle
        # Folgeneintraege bekannt sind. Hoster- und Stream-URLs bleiben dabei
        # ausschliesslich im normalen Wiedergabefluss, nie in der Queue.
        if oGuiElement._mediaType in ('movie', 'episode'):
            values = oGuiElement.getItemValues()
            watchId = playbackstate.itemKey(
                oGuiElement.getSiteName(), oGuiElement.getTitle(),
                values.get('season', ''), values.get('episode', ''),
                values.get('TVShowTitle', ''), params.getValue('sUrl'))
            params.setParam('watchId', watchId)
            oGuiElement.addItemProperties('GerXStream.WatchId', watchId)
        savedTarget = oGuiElement.getItemProperties().get('GerXStream.Target', '')
        trackEpisode = (oGuiElement._mediaType == 'episode' and not isHoster and not savedTarget
                and not oGuiElement.getItemProperties().get('epicFavoritesManaged'))
        if trackEpisode:
            queue = self._episodeQueues.setdefault(
                self._episodeQueueKey, {'id': uuid.uuid4().hex, 'targets': []})
            params.setParam('episodeQueue', queue['id'])
            params.setParam('episodeIndex', len(queue['targets']))
        queueEnabled = trackEpisode and cConfig().getSettingBool('autoNextEpisodeEnabled', False)
        if trackEpisode:
            from resources.lib import epicfavorites
            incoming = ParameterHandler()
            parent = incoming.getValue('watchlistTarget') or xbmc.getInfoLabel('Container.FolderPath')
            if not parent and len(sys.argv) > 2 and self.pluginPath.startswith('plugin://'):
                parent = self.pluginPath + sys.argv[2]
            parent = epicfavorites.normaliseTarget(parent)
            parentRoute = dict(parse_qsl(urlsplit(parent).query))
            if (urlsplit(parent).netloc != urlsplit(self.pluginPath).netloc
                    or parentRoute.get('site') != oGuiElement.getSiteName()):
                parent = ''
            params.setParam('watchlistTarget', parent)
            params.setParam('watchlistTitle', incoming.getValue('watchlistTitle')
                            or oGuiElement.getItemValues().get('TVShowTitle', '')
                            or incoming.getValue('TVShowTitle') or '')
            params.setParam('watchlistYear', incoming.getValue('watchlistYear') or '')
        sUrl = savedTarget or self.__createItemUrl(oGuiElement, False if queueEnabled else bIsFolder, params)
        if not savedTarget and params.getValue('watchlistTarget') and sUrl.startswith('plugin://plugin.video.gerxstream/'):
            parsed = urlsplit(sUrl)
            query = dict(parse_qsl(parsed.query))
            for key in ('watchlistTarget', 'watchlistTitle', 'watchlistYear', 'watchlistIsFolder'):
                query[key] = params.getValue(key) or ''
            sUrl = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ''))
        if (not isHoster and not savedTarget and oGuiElement._mediaType in ('tvshow', 'movie')
                and sUrl.startswith('plugin://plugin.video.gerxstream/')):
            from resources.lib import epicfavorites
            parsed = urlsplit(sUrl)
            query = dict(parse_qsl(parsed.query))
            query.update(watchlistTarget=epicfavorites.normaliseTarget(sUrl),
                         watchlistTitle=(epicfavorites.seriesName(oGuiElement.getTitle())
                                         if oGuiElement._mediaType == 'tvshow' else oGuiElement.getTitle()),
                         watchlistYear=oGuiElement._sYear,
                         watchlistIsFolder=str(bool(bIsFolder)).lower())
            sUrl = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ''))
        contextUrl = sUrl
        if trackEpisode:
            self._episodeQueues[self._episodeQueueKey]['targets'].append(sUrl)
        startEpisodeQueue = (queueEnabled
                             and sUrl.startswith('plugin://plugin.video.gerxstream/'))
        if startEpisodeQueue:
            bIsFolder = False
            sUrl = '%s?%s' % (self.pluginPath, urlencode({
                'site': 'cHosterGui', 'function': 'play', 'episodeStart': '1',
                'episodeQueue': params.getValue('episodeQueue'),
                'episodeIndex': params.getValue('episodeIndex'),
                'mediaType': 'episode', 'title': oGuiElement.getTitle(),
            }))
#kasi
        try:
            if params.exist('trumb'): oGuiElement.setIcon(params.getValue('trumb'))
        except Exception:
            pass

        listitem = self.createListItem(oGuiElement)
        if not bIsFolder and not startEpisodeQueue and cConfig().getSetting('hosterSelect') == 'List':
            bIsFolder = True
        if isHoster:
            bIsFolder = False
        listitem = self.__createContextMenu(oGuiElement, listitem, bIsFolder, contextUrl,
                          sUrl if startEpisodeQueue else '')
        if not bIsFolder:
            listitem.setProperty('IsPlayable', 'false' if startEpisodeQueue else 'true')
        xbmcplugin.addDirectoryItem(self.pluginHandle, sUrl, listitem, bIsFolder, iTotal)

    def addNextPage(self, site, function, params=''):
        guiElement = cGuiElement(cConfig().getLocalizedString(30279), site, function)
        self.addFolder(guiElement, params)

    def searchNextPage(self, sTitle, site, function, params=''):
        guiElement = cGuiElement(sTitle, site, function)
        self.addFolder(guiElement, params)

    def createListItem(self, oGuiElement):
        itemValues = oGuiElement.getItemValues()
        itemTitle = oGuiElement.getItemProperties().get('GerXStream.DisplayTitle') or oGuiElement.getTitle()
        infoString = ''
        if self.globalSearch: # Reihenfolge der zu anzeigenden GUI Elemente
            infoString += ' %s' % oGuiElement.getSiteName()
        if oGuiElement._sLanguage != '':
            infoString += ' (%s)' % oGuiElement._sLanguage
        if oGuiElement._sSubLanguage != '':
            infoString += ' *Sub: %s*' % oGuiElement._sSubLanguage
        if oGuiElement._sQuality != '':
            infoString += ' [%s]' % oGuiElement._sQuality
        if oGuiElement._sInfo != '':
            infoString += ' [%s]' % oGuiElement._sInfo
        # if self.globalSearch:
        #     infoString += ' %s' % oGuiElement.getSiteName()
        if infoString:
            infoString = '[I]%s[/I]' % infoString
        itemValues['title'] = itemTitle + infoString
        try:
            if not 'plot' in str(itemValues) or itemValues['plot'] == '':
                itemValues['plot'] = ' ' #kasi Alt 255
        except Exception:
            pass
        #listitem = xbmcgui.ListItem(itemTitle + infoString, oGuiElement.getIcon(), oGuiElement.getThumbnail())
        listitem = xbmcgui.ListItem(itemTitle + infoString)
        self.setInfoTagVideo(oGuiElement, listitem)

        listitem.setProperty('fanart_image', oGuiElement.getFanart())
        listitem.setArt({'icon': oGuiElement.getIcon(), 'thumb': oGuiElement.getThumbnail(), 'poster': oGuiElement.getThumbnail(), 'fanart': oGuiElement.getFanart()})
        aProperties = oGuiElement.getItemProperties()
        if len(aProperties) > 0:
            for sPropertyKey in aProperties.keys():
                listitem.setProperty(sPropertyKey, aProperties[sPropertyKey])
        watchId = aProperties.get('GerXStream.WatchId', '')
        if watchId:
            listitem.getVideoInfoTag().setUniqueID(watchId, 'gerxstream')
        if playbackstate.isWatched(watchId):
            listitem.getVideoInfoTag().setPlaycount(1)
            listitem.getVideoInfoTag().setResumePoint(0, 0)
        return listitem

    ### ÄNDERUNG ANFANG ###
    def setInfoTagVideo(self, oGuiElement, listitem):
        itemValues = oGuiElement.getItemValues()
        vtag = listitem.getVideoInfoTag()

        vtag.setMediaType(oGuiElement.getType())

        # itemValues['title'] enthaelt bereits Label + Infostring (siehe createListItem)
        if 'title' in itemValues:
            try:
                vtag.setTitle(str(itemValues['title']))
            except: pass
        if 'plot' in itemValues:
            try:
                vtag.setPlot(itemValues['plot'])
            except: pass
        if 'year' in itemValues:
            try:
                vtag.setYear(int(itemValues['year']))
            except: pass
        if 'season' in itemValues:
            try:
                vtag.setSeason(int(itemValues['season']))
            except: pass
        if 'episode' in itemValues:
            try:
                vtag.setEpisode(int(itemValues['episode']))
            except: pass
        if 'TVShowTitle' in itemValues:
            try:
                vtag.setTvShowTitle(itemValues['TVShowTitle'])
            except: pass
        if 'cast' in itemValues:
            try:
                vtag.setCast([xbmc.Actor(cast[0], cast[1], thumbnail=cast[2]) for cast in itemValues['cast']])
            except: pass
        if 'countries' in itemValues:
            try:
                vtag.setCountries(itemValues['countries'])
            except: pass
        if 'country' in itemValues:
            try:
                vtag.setCountries([itemValues['country']])
            except: pass
        if 'dateadded' in itemValues:
            try:
                vtag.setDateAdded(itemValues['dateadded'])
            except: pass
        if 'directors' in itemValues:
            try:
                vtag.setDirectors(itemValues['directors'])
            except: pass
        # tmdb.py liefert 'director' und 'writer' als ' / '-getrennte Strings
        if 'director' in itemValues:
            try:
                vtag.setDirectors([d.strip() for d in str(itemValues['director']).split(' / ') if d.strip()])
            except: pass
        if 'writer' in itemValues:
            try:
                vtag.setWriters([w.strip() for w in str(itemValues['writer']).split(' / ') if w.strip()])
            except: pass
        if 'duration' in itemValues:
            # minuten in sekunden umrechnen
            try:
                vtag.setDuration(int(itemValues['duration']) * 60)
            except: pass
        if 'rating' in itemValues:
            try:
                vtag.setRating(float(itemValues['rating']))
            except: pass
        if 'imdb_rating' in itemValues:
            # IMDb-Wertung aus OMDb zusaetzlich zur TMDB-Wertung (plotinfo.py)
            try:
                ratings = {'imdb': (float(itemValues['imdb_rating'][0]), int(itemValues['imdb_rating'][1]))}
                if 'rating' in itemValues:
                    ratings['themoviedb'] = (float(itemValues['rating']), int(itemValues.get('votes') or 0))
                vtag.setRatings(ratings, 'imdb')
            except: pass
        if 'votes' in itemValues:
            try:
                vtag.setVotes(int(itemValues['votes']))
            except: pass
        if 'code' in itemValues:
            try:
                vtag.setProductionCode(str(itemValues['code']))
            except: pass
        if 'aired' in itemValues:
            try:
                vtag.setFirstAired(str(itemValues['aired']))
            except: pass
        if 'status' in itemValues:
            try:
                vtag.setTvShowStatus(str(itemValues['status']))
            except: pass
        if 'genre' in itemValues:
            try:
                vtag.setGenres(itemValues['genre'].split(' / '))
            except: pass
        if 'imdb_id' in itemValues:
            try:
                vtag.setUniqueID(str(itemValues['imdb_id']), 'imdb')
            except: pass
        if 'tmdb_id' in itemValues:
            try:
                vtag.setUniqueID(str(itemValues['tmdb_id']), 'tmdb')
            except: pass
        if 'originaltitle' in itemValues:
            try:
                vtag.setOriginalTitle(itemValues['originaltitle'])
            except: pass
        if 'trailer' in itemValues:
            try:
                vtag.setTrailer(itemValues['trailer'])
            except: pass
        if 'tagline' in itemValues:
            try:
                vtag.setTagLine(itemValues['tagline'])
            except: pass
        # Kodi versucht Bilder er Studios zu finden, was zu Fehlern im Logfile führt
        #if 'studio' in itemValues:
        #    try:
        #        vtag.setStudios(itemValues['studio'].split(' / '))
        #    except: pass
        if 'premiered' in itemValues:
            try:
                vtag.setPremiered(itemValues['premiered'])
            except: pass
    ### ÄNDERUNG ENDE ###


    def __createContextMenu(self, oGuiElement, listitem, bIsFolder, sUrl, episodeStartUrl=''):
        contextmenus = []
        if len(oGuiElement.getContextItems()) > 0:
            for contextitem in oGuiElement.getContextItems():
                params = contextitem.getOutputParameterHandler()
                sParams = params.getParameterAsUri()
                sTest = "%s?site=%s&function=%s&%s" % (self.pluginPath, contextitem.getFile(), contextitem.getFunction(), sParams)
                contextmenus += [(contextitem.getTitle(), "RunPlugin(%s)" % (sTest,),)]
        itemValues = oGuiElement.getItemValues()
        contextitem = cContextElement()
        # Eigene, verschachtelte GerXStream-Favoriten. Der originale
        # Plugin-Aufruf wird gespeichert, nicht die (kurzlebige) Stream-URL;
        # deshalb funktionieren Favoriten auch nach einem Hosterwechsel.
        # Eintraege innerhalb von Epic-Favorites selbst markieren sich, damit
        # dort nicht noch einmal "Hinzufuegen" erscheint.
        if not oGuiElement.getItemProperties().get('epicFavoritesManaged'):
            from resources.lib import epicfavorites
            favoriteParams = {
                'target': sUrl,
                'title': oGuiElement.getTitle(),
                'isFolder': str(bool(bIsFolder)).lower(),
                'thumbnail': oGuiElement.getThumbnail(),
                'fanart': oGuiElement.getFanart(),
                'description': oGuiElement.getDescription(),
                'mediaType': oGuiElement._mediaType,
            }
            route = dict(parse_qsl(urlsplit(sUrl).query))
            favoriteParams.update(seriesTitle=route.get('watchlistTitle', ''),
                                  seriesTarget=route.get('watchlistTarget', ''),
                                  year=route.get('watchlistYear', ''), source=route.get('site', ''))
            favoriteTitle = cConfig().getLocalizedString(30918) % epicfavorites.displayName()
            contextmenus += [(favoriteTitle, "RunPlugin(%s?function=addEpicFavorite&%s)" %
                             (self.pluginPath, urlencode(favoriteParams)))]
            if oGuiElement._mediaType in ('movie', 'tvshow', 'season', 'episode'):
                contextmenus += [(cConfig().getLocalizedString(31855),
                                  'RunPlugin(%s?site=epicFavorites&function=setWatchlistStatus&%s)' %
                                  (self.pluginPath, urlencode(favoriteParams)))]
        if oGuiElement._mediaType == 'movie' or oGuiElement._mediaType == 'tvshow':
            if cConfig().getSettingBool('gerxstream.trailer', False):
                if not xbmc.getCondVisibility('System.HasAddon(%s)' % 'script.module.xstream.trailer'):  # Schauen ob Addon installiert
                    xbmc.executebuiltin('InstallAddon(%s)' % 'script.module.xstream.trailer')  # Addon installieren
                contextitem.setTitle(cConfig().getLocalizedString(30027))  # Trailer Funktion
                contextmenus += [(contextitem.getTitle(), "RunPlugin(plugin://script.module.xstream.trailer/?action=play&name=%s&url=&language=)" % (itemValues['title'],),)]
        if oGuiElement._mediaType == 'movie' or oGuiElement._mediaType == 'tvshow':
            contextitem.setTitle(cConfig().getLocalizedString(30239))   # Erweiterte Info
            searchParams = {'searchTitle': oGuiElement.getTitle(), 'sMeta': oGuiElement._mediaType, 'sYear': oGuiElement._sYear}
            contextmenus += [(contextitem.getTitle(), "RunPlugin(%s?function=viewInfo&%s)" % (self.pluginPath, urlencode(searchParams),),)]
        if oGuiElement._mediaType == 'season' or oGuiElement._mediaType == 'episode':
            contextitem.setTitle(cConfig().getLocalizedString(30241))   # Info
            contextmenus += [(contextitem.getTitle(), cConfig().getLocalizedString(30242),)]    # Action(Info)
        # search for alternative source
        contextitem.setTitle(cConfig().getLocalizedString(30243))   # Weitere Quellen
        searchParams = {'searchTitle': oGuiElement.getTitle()}
        if 'imdb_id' in itemValues:
            searchParams['searchImdbID'] = itemValues['imdb_id']
        contextmenus += [(contextitem.getTitle(), "Container.Update(%s?function=searchAlter&%s)" % (self.pluginPath, urlencode(searchParams),),)]
        if 'imdb_id' in itemValues and 'title' in itemValues:
            metaParams = {}
            if itemValues['title']:
                metaParams['title'] = oGuiElement.getTitle()
            if 'mediaType' in itemValues and itemValues['mediaType']:
                metaParams['mediaType'] = itemValues['mediaType']
            elif 'TVShowTitle' in itemValues and itemValues['TVShowTitle']:
                metaParams['mediaType'] = 'tvshow'
            else:
                metaParams['mediaType'] = 'movie'
            if 'season' in itemValues and itemValues['season'] and int(itemValues['season']) > 0:
                metaParams['season'] = itemValues['season']
                metaParams['mediaType'] = 'season'
            if 'episode' in itemValues and itemValues['episode'] and int(itemValues['episode']) > 0 and 'season' in itemValues and itemValues['season'] and int(itemValues['season']):
                metaParams['episode'] = itemValues['episode']
                metaParams['mediaType'] = 'episode'

        # context options for movies or episodes
        if not bIsFolder:
            contextitem.setTitle(cConfig().getLocalizedString(30244))   # Playlist hinzufügen
            contextmenus += [(contextitem.getTitle(), "RunPlugin(%s&playMode=enqueue)" % (sUrl,),)]
            contextitem.setTitle(cConfig().getLocalizedString(30245))   # Download
            contextmenus += [(contextitem.getTitle(), "RunPlugin(%s&playMode=download)" % (sUrl,),)]
            if cConfig().getSettingBool('jd_enabled', False):
                contextitem.setTitle(cConfig().getLocalizedString(30246))   # send JD
                contextmenus += [(contextitem.getTitle(), "RunPlugin(%s&playMode=jd)" % (sUrl,),)]
            if cConfig().getSettingBool('jd2_enabled', False):
                contextitem.setTitle(cConfig().getLocalizedString(30247))   # Send JD2
                contextmenus += [(contextitem.getTitle(), "RunPlugin(%s&playMode=jd2)" % (sUrl,),)]
            if cConfig().getSettingBool('myjd_enabled', False):
                contextitem.setTitle(cConfig().getLocalizedString(30248))   # Send myjd
                contextmenus += [(contextitem.getTitle(), "RunPlugin(%s&playMode=myjd)" % (sUrl,),)]
            if cConfig().getSettingBool('pyload_enabled', False):
                contextitem.setTitle(cConfig().getLocalizedString(30250))   # Send Pyload
                contextmenus += [(contextitem.getTitle(), "RunPlugin(%s&playMode=pyload)" % (sUrl,),)]
            # Immer verfuegbar: umgeht automatisches Abspielen, bevorzugte
            # Hoster mit Autostart und den gemerkten Hoster der Folgenliste.
            contextitem.setTitle(cConfig().getLocalizedString(31400))   # Mit Hoster-Auswahl abspielen
            manualAction = ("RunPlugin(%s&manual=1)" % episodeStartUrl if episodeStartUrl else
                            "RunPlugin(%s&playMode=play&manual=1)" % sUrl)
            contextmenus += [(contextitem.getTitle(), manualAction)]
        listitem.addContextMenuItems(contextmenus)
        # listitem.addContextMenuItems(contextmenus, True)
        return listitem

    def setEndOfDirectory(self, success=True):
        # mark the listing as completed, this is mandatory
        episodeQueue = self._episodeQueues.pop(self._episodeQueueKey, None)
        if episodeQueue and episodeQueue['targets']:
            from resources.lib import episodequeue
            episodequeue.store(episodeQueue['id'], episodeQueue['targets'])
        if not self._isViewSet:
            self.setView('files')
        xbmcplugin.setPluginCategory(self.pluginHandle, "")
        # add some sort methods, these will be available in all views
        xbmcplugin.addSortMethod(self.pluginHandle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(self.pluginHandle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
        xbmcplugin.addSortMethod(self.pluginHandle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(self.pluginHandle, xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(self.pluginHandle, xbmcplugin.SORT_METHOD_PROGRAM_COUNT)
        xbmcplugin.addSortMethod(self.pluginHandle, xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
        xbmcplugin.addSortMethod(self.pluginHandle, xbmcplugin.SORT_METHOD_GENRE)
        xbmcplugin.endOfDirectory(self.pluginHandle, success)

    def setView(self, content='movies'):
        # set the listing to a certain content, makes special views available
        # sets view to the viewID which is selected in GerXStream settings
        # see http://mirrors.xbmc.org/docs/python-docs/stable/xbmcplugin.html#-setContent
        # (seasons is also supported but not listed)
        content = content.lower()
        supportedViews = ['files', 'songs', 'artists', 'albums', 'movies', 'tvshows', 'seasons', 'episodes', 'musicvideos']
        if content in supportedViews:
            self._isViewSet = True
            xbmcplugin.setContent(self.pluginHandle, content)
        if cConfig().getSettingBool('auto-view', False) and content:
            viewId = cConfig().getSetting(content + '-view')
            if viewId:
                xbmc.executebuiltin("Container.SetViewMode(%s)" % viewId)

    def updateDirectory(self):
        # update the current listing
        xbmc.executebuiltin("Container.Refresh")

    def __createItemUrl(self, oGuiElement, bIsFolder, params=''):
        if params == '':
            params = ParameterHandler()
        itemValues = oGuiElement.getItemValues()
        if 'tmdb_id' in itemValues and itemValues['tmdb_id']:
            params.setParam('tmdbID', itemValues['tmdb_id'])
        if 'TVShowTitle' in itemValues and itemValues['TVShowTitle']:
            params.setParam('TVShowTitle', itemValues['TVShowTitle'])
        if 'season' in itemValues and itemValues['season'] and int(itemValues['season']) > 0:
            params.setParam('season', itemValues['season'])
        if 'episode' in itemValues and itemValues['episode'] and float(itemValues['episode']) > 0:
            params.setParam('episode', itemValues['episode'])
        # TODO change this, it can cause bugs it influencec the params for the following listitems
        if not bIsFolder:
            params.setParam('MovieTitle', oGuiElement.getTitle())
            thumbnail = oGuiElement.getThumbnail()
            if thumbnail:
                params.setParam('thumb', thumbnail)
            if oGuiElement._mediaType:
                params.setParam('mediaType', oGuiElement._mediaType)
            elif 'TVShowTitle' in itemValues and itemValues['TVShowTitle']:
                params.setParam('mediaType', 'tvshow')
            if 'season' in itemValues and itemValues['season'] and int(itemValues['season']) > 0:
                params.setParam('mediaType', 'season')
            if 'episode' in itemValues and itemValues['episode'] and float(itemValues['episode']) > 0:
                params.setParam('mediaType', 'episode')
        sParams = params.getParameterAsUri()
        try:
            if params.getValue('sUrl').startswith("plugin://"):
                return  params.getValue('sUrl')
        except: pass
        if len(oGuiElement.getFunction()) == 0:
            sUrl = "%s?site=%s&title=%s&%s" % (self.pluginPath, oGuiElement.getSiteName(), quote_plus(oGuiElement.getTitle()), sParams)
        else:
            #kasi
            sUrl = "%s?site=%s&function=%s&title=%s&trumb=%s&%s" % (self.pluginPath, oGuiElement.getSiteName(), oGuiElement.getFunction(), quote_plus(oGuiElement.getTitle()), oGuiElement.getThumbnail(), sParams)
            if not bIsFolder:
                sUrl += '&playMode=play'
        return sUrl

    @staticmethod
    def showKeyBoard(sDefaultText="", sHeading=""):
        # Create the keyboard object and display it modal
        oKeyboard = xbmc.Keyboard(sDefaultText, sHeading)
        oKeyboard.doModal()
        # If key board is confirmed and there was text entered return the text
        if oKeyboard.isConfirmed():
            sSearchText = oKeyboard.getText()
            if len(sSearchText) > 0:
                return sSearchText
        return False

    @staticmethod
    def showNumpad(defaultNum="", numPadTitle=None):
        if numPadTitle is None:
            numPadTitle = cConfig().getLocalizedString(30251)
        defaultNum = str(defaultNum)
        dialog = xbmcgui.Dialog()
        num = dialog.numeric(0, numPadTitle, defaultNum)
        return num

    @staticmethod
    def openSettings():
        cConfig().showSettingsWindow()

    @staticmethod
    def showNofication(sTitle, iSeconds=0):
        if iSeconds == 0:
            iSeconds = 1000
        else:
            iSeconds = iSeconds * 1000
        xbmc.executebuiltin("Notification(%s,%s,%s,%s)" % (cConfig().getLocalizedString(30308), (cConfig().getLocalizedString(30309) % str(sTitle)), iSeconds, cConfig().getAddonInfo('icon')))

    @staticmethod
    def showError(sTitle, sDescription, iSeconds=0):
        if iSeconds == 0:
            iSeconds = 1000
        else:
            iSeconds = iSeconds * 1000
        xbmc.executebuiltin("Notification(%s,%s,%s,%s)" % (str(sTitle), (str(sDescription)), iSeconds, cConfig().getAddonInfo('icon')))

    @staticmethod
    def showInfo(sTitle='GerXStream', sDescription=None, iSeconds=0):
        if sDescription is None:
            sDescription = cConfig().getLocalizedString(30253)
        if iSeconds == 0:
            iSeconds = 1000
        else:
            iSeconds = iSeconds * 1000
        xbmc.executebuiltin("Notification(%s,%s,%s,%s)" % (str(sTitle), (str(sDescription)), iSeconds, cConfig().getAddonInfo('icon')))

    @staticmethod
    def showLanguage(sTitle='GerXStream', sDescription=None, iSeconds=0):
        if sDescription is None:
            sDescription = cConfig().getLocalizedString(30403)
        if iSeconds == 0:
            iSeconds = 1000
        else:
            iSeconds = iSeconds * 1000
        xbmc.executebuiltin("Notification(%s,%s,%s,%s)" % (str(sTitle), (str(sDescription)), iSeconds, cConfig().getAddonInfo('icon')))
