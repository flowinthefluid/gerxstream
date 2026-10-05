# -*- coding: utf-8 -*-
# Python 3

import sys
import xbmc
import xbmcgui
import xbmcplugin
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.handler.pluginHandler import cPluginHandler
from xbmc import LOGINFO as LOGNOTICE, LOGERROR
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.gui.contextElement import cContextElement
from resources.lib.gui.gui import cGui
from resources.lib.config import cConfig
from resources.lib.tools import logger, cParser, cCache, addon_log as log

SCRAPER_ENTRY_FUNCTIONS = frozenset((
    '_showGenreMenu',
    'ajaxCall',
    'getHosterUrl',
    'getHosterUrl_1',
    'getHosterUrl_2',
    'getHosterUrl_3',
    'getHosterUrl_4',
    'getHosterUrl_6',
    'load',
    'menuCollections',
    'parseMovieEntrySite',
    'parseNews',
    'showAllSeries',
    'showCharacters',
    'showCinemaMovies',
    'showCollection',
    'showCollectionEntries',
    'showCollections',
    'showCountry',
    'showDocuMenu',
    'showDoku_6',
    'showEntries',
    'showEntriesLast',
    'showEntriesUnJson',
    'showEntries_1',
    'showEntries_2',
    'showEntries_3',
    'showEntries_4',
    'showEntries_6',
    'showEpisodeHosters',
    'showEpisodes',
    'showEpisodes_2',
    'showFavItems',
    'showGenre',
    'showGenreEntries',
    'showGenreMMenu',
    'showGenreMenu',
    'showGenreSMenu',
    'showGenre_1',
    'showGenre_2',
    'showGenre_3',
    'showGenre_4',
    'showGenres',
    'showHosters',
    'showHostersUnJson',
    'showHosters_1',
    'showHosters_2',
    'showHosters_3',
    'showHosters_4',
    'showHosters_6',
    'showMovieMenu',
    'showMovieCategories',
    'showNewEpisodes',
    'showNewSeries',
    'showNews',
    'showSearch',
    'showSearchActor',
    'showSearchMovies',
    'showSearchPage',
    'showSearchSeries',
    'showSearch_1',
    'showSearch_2',
    'showSearch_3',
    'showSearch_4',
    'showSearch_6',
    'showSeasons',
    'showSeries',
    'showSeriesCategories',
    'showSeriesEpisodes',
    'showSeriesMenu',
    'showShows',
    'showStart',
    'showThemen_6',
    'showValue',
    'showYTChannels',
    'showYTGenre',
    'showYTLists',
    'showYTMore',
    'showYTSearch',
    'showYears',
    'showYearsMenu',
))

HOSTER_GUI_FUNCTIONS = frozenset((
    'addToPlaylist',
    'download',
    'play',
    'sendToJDownloader',
    'sendToJDownloader2',
    'sendToMyJDownloader',
    'sendToPyLoad',
))


MAIN_MENU_ORDER_SETTING = 'mainMenuOrder'
MAIN_MENU_ORDER_DEFAULT = ('epicFavorites', 'globalSearch', 'sourceCategories', 'livestreams', 'categories', 'random', 'history', 'settings')


def _mainMenuOrder():
    """Liest die gespeicherte Hauptmenue-Reihenfolge defensiv ein.

    Ein altes oder manuell veraendertes Setting kann keine Eintraege
    verschwinden lassen: unbekannte Kennungen werden verworfen, neue
    Standardpunkte werden hinten angehaengt.
    """
    raw = cConfig().getSetting(MAIN_MENU_ORDER_SETTING, '')
    chosen = []
    for key in (raw or '').split(','):
        key = key.strip()
        if key in MAIN_MENU_ORDER_DEFAULT and key not in chosen:
            chosen.append(key)
    for key in MAIN_MENU_ORDER_DEFAULT:
        if key not in chosen:
            chosen.append(key)
    # Epic-Favorites ist der persoenliche Startpunkt und steht absichtlich
    # stets vor der globalen Suche - auch bei bereits gespeicherten alten
    # Menue-Reihenfolgen ohne diese neue Kennung.
    chosen.remove('epicFavorites')
    chosen.insert(0, 'epicFavorites')
    return chosen


def showMainMenuOrder():
    """Kleiner Kodi-Dialog zum schrittweisen Verschieben der Hauptmenuepunkte."""
    labels = {
        'epicFavorites': cConfig().getSetting('epicFavoritesName', 'Epic-Favorites'),
        'globalSearch': cConfig().getLocalizedString(30040),
        'sourceCategories': cConfig().getLocalizedString(30878),
        'livestreams': cConfig().getLocalizedString(30989),
        'categories': cConfig().getLocalizedString(30507),
        'random': cConfig().getLocalizedString(30868),
        'history': cConfig().getLocalizedString(30903),
        'settings': cConfig().getLocalizedString(30041),
    }
    order = _mainMenuOrder()
    dialog = xbmcgui.Dialog()
    while True:
        display = ['%s. %s' % (index + 1, labels[key])
                   for index, key in enumerate(order)]
        selected = dialog.select(cConfig().getLocalizedString(30879), display)
        if selected < 0:
            break
        action = dialog.select(labels[order[selected]],
                               [cConfig().getLocalizedString(30880),
                                cConfig().getLocalizedString(30881),
                                cConfig().getLocalizedString(30882)])
        if action == 0 and selected > 0:
            order[selected - 1], order[selected] = order[selected], order[selected - 1]
        elif action == 1 and selected < len(order) - 1:
            order[selected + 1], order[selected] = order[selected], order[selected + 1]
        elif action == 2:
            order = list(MAIN_MENU_ORDER_DEFAULT)

    cConfig().setSetting(MAIN_MENU_ORDER_SETTING, ','.join(order))
    xbmc.executebuiltin('Container.Refresh')


def _endFailedDirectory():
    try:
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=False)
    except (IndexError, ValueError):
        pass


def _rejectPluginRoute(sSiteName, sFunction, sReason):
    log(cConfig().getLocalizedString(30166) +
        " -> [gerxstream]: Rejected plugin route site=%r function=%r: %s" %
        (sSiteName, sFunction, sReason), LOGERROR)
    _endFailedDirectory()


def _isAllowedScraperRoute(sSiteName, sFunction):
    if sSiteName not in cPluginHandler().getPluginNames():
        _rejectPluginRoute(sSiteName, sFunction, 'site is not a scraper module')
        return False
    if sFunction not in SCRAPER_ENTRY_FUNCTIONS:
        _rejectPluginRoute(sSiteName, sFunction, 'function is not allowed')
        return False
    return True


try:
    import resolveurl as resolver
except ImportError:
    # Resolver Fehlermeldung (bei defekten oder nicht installierten Resolver)
    xbmcgui.Dialog().ok(cConfig().getLocalizedString(30119), cConfig().getLocalizedString(30120))
    # Ohne Resolver ist kein sinnvoller Betrieb moeglich. Das Listing muss als
    # fehlgeschlagen abgeschlossen werden, sonst wartet Kodi auf Eintraege, die
    # nie kommen. Danach abbrechen, statt weiterzulaufen und beim ersten Zugriff
    # auf 'resolver' mit NameError zu sterben.
    log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: resolveurl not available, aborting', LOGERROR)
    _endFailedDirectory()
    sys.exit()


def viewInfo(params):
    from resources.lib.tmdbinfo import WindowsBoxes
    parms = ParameterHandler()
    sCleanTitle = params.getValue('searchTitle')
    sMeta = parms.getValue('sMeta')
    sYear = parms.getValue('sYear')
    WindowsBoxes(sCleanTitle, sCleanTitle, sMeta, sYear)


def parseUrl():
    if xbmc.getInfoLabel('Container.PluginName') == 'plugin.video.osmosis':
        sys.exit()

    params = ParameterHandler()
    logger.info(params.getAllParameters())

    # If no function is set, we set it to the default "load" function
    if params.exist('function'):
        sFunction = params.getValue('function')
        if sFunction == 'spacer':
            return True
        elif sFunction == 'clearCache':
            cRequestHandler('dummy').clearCache()
            return
        elif sFunction == 'viewInfo':
            viewInfo(params)
            return
        elif sFunction == 'searchAlter':
            searchAlter(params)
            return
        elif sFunction == 'searchTMDB':
            searchTMDB(params)
            return
        elif sFunction == 'devUpdates':
            from resources.lib import updateManager
            updateManager.devUpdates()
            cGui().setEndOfDirectory()
            return
        elif sFunction == 'gerxstreamUpdate':
            updateGerXStream()
            cGui().setEndOfDirectory()
            return
        elif sFunction == 'pluginInfo':
            cPluginHandler().pluginInfo()
            cGui().setEndOfDirectory()
            return
        elif sFunction == 'vod':
            vodGuiElements(sFunction)
            return
        elif sFunction == 'categories':
            from resources.lib import categories
            categories.showMenu()
            return
        elif sFunction == 'peopleGroups':
            from resources.lib import categories
            categories.editPeopleGroups(params)
            return
        elif sFunction == 'randomMovies':
            showRandomMovies()
            return
        elif sFunction == 'clearWatchHistory':
            clearWatchHistory()
            return
        elif sFunction == 'addEpicFavorite':
            addEpicFavorite(params)
            return
        elif sFunction == 'mainMenuOrder':
            showMainMenuOrder()
            return
        elif sFunction == 'livestreamsRefresh':
            from resources.lib.livestreams import route as ls_route
            ls_route.run_refresh()
            return
        elif sFunction == 'livestreamsExportHint':
            from resources.lib.livestreams import route as ls_route
            ls_route.run_export_hint()
            return
        elif sFunction == 'livestreamsVerify':
            from resources.lib.livestreams import verification
            verification.report_dialog()
            return
        elif sFunction == 'livestreamsRabbithole':
            # Einstieg fuer den optionalen Keymap (Down = naechste Webcam).
            from resources.lib.livestreams import route as ls_route
            ls_route.rabbithole_next(params)
            return
        elif sFunction == 'lsCountriesEditor':
            from resources.lib.livestreams import settings_ui
            settings_ui.edit_countries()
            return
        elif sFunction == 'lsGenresEditor':
            from resources.lib.livestreams import settings_ui
            settings_ui.edit_genres()
            return
        elif sFunction == 'lsRabbitholeCategories':
            from resources.lib.livestreams import settings_ui
            settings_ui.edit_rh_categories()
            return
        elif sFunction == 'showBackupMenu':
            showBackupMenu()
            return
        elif sFunction == 'runBackupAction':
            runBackupAction(params)
            return
        elif sFunction == 'showContentCategory':
            showContentCategory(params)
            return
        elif sFunction == 'showDomains':
            showDomainMenu(params)
            return
        elif sFunction == 'setSiteDomain':
            setSiteDomain(params)
            return
        elif sFunction == 'blockedHosterMenu':
            showBlockedHosterMenu()
            return
        elif sFunction == 'preferredHosterMenu':
            showPreferredHosterMenu()
            return
        elif sFunction == 'cookieAssistant':
            from resources.lib import cookieassistant
            source = params.getValue('source')
            cookieassistant.run(source if isinstance(source, str) and re.fullmatch(r'[a-z0-9_\-]+', source) else None)
            return
        elif sFunction == 'changelog':
            from resources.lib import tools
            cConfig().setSetting('changelog_version', '')
            tools.changelog()
            return
        elif sFunction == 'devWarning':
            from resources.lib import tools
            tools.devWarning()
            return

    elif params.exist('remoteplayurl'):
        try:
            remotePlayUrl = params.getValue('remoteplayurl')
            sLink = resolver.resolve(remotePlayUrl)
            if sLink:
                xbmc.executebuiltin('PlayMedia(' + sLink + ')')
            else:
                log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: Could not play remote url %s ' % sLink, LOGNOTICE)
        except resolver.resolver.ResolverError as e:
            log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: ResolverError: %s' % e, LOGERROR)
        return
    else:
        sFunction = 'load'

    # Test if we should run a function on a special site
    if not params.exist('site'):
        # As a default if no site was specified, we run the default starting gui with all plugins
        showMainMenu(sFunction)
        return
    sSiteName = params.getValue('site')
    if params.exist('playMode'):
        # Livestream-Wiedergabe hat einen eigenen Auswahl-/Failover-Weg und
        # laeuft nicht ueber die Scraper-Hoster-Logik.
        if sSiteName == 'livestreams':
            from resources.lib.livestreams import route as ls_route
            ls_route.play(params)
            return
        if not _isAllowedScraperRoute(sSiteName, sFunction):
            return
        from resources.lib.gui.hoster import cHosterGui
        url = False
        playMode = params.getValue('playMode')
        isHoster = params.getValue('isHoster')
        url = params.getValue('url')
        manual = params.exist('manual')

        if cConfig().getSetting('hosterSelect') == 'Auto' and playMode != 'jd' and playMode != 'jd2' and playMode != 'pyload' and not manual:
            cHosterGui().streamAuto(playMode, sSiteName, sFunction)
        else:
            cHosterGui().stream(playMode, sSiteName, sFunction, url, manual=manual)
        return

    log(cConfig().getLocalizedString(30166) + " -> [gerxstream]: Call function '%s' from '%s'" % (sFunction, sSiteName), LOGNOTICE)
    # If the hoster gui is called, run the function on it and return
    if sSiteName == 'cHosterGui':
        showHosterGui(sFunction)
    # If global search is called
    elif sSiteName == 'globalSearch':
        if sFunction == 'searchGlobal':
            scope = params.getValue('searchScope') if params.exist('searchScope') else 'alle'
            searchGlobal(params.getValue('searchterm'), scope)
        else:
            showGlobalSearchMenu()
    elif sSiteName == 'history':
        if sFunction == 'showWatchHistory':
            showWatchHistory()
        elif sFunction == 'resumeWatchHistory':
            resumeWatchHistory(params)
        else:
            _endFailedDirectory()
    elif sSiteName == 'epicFavorites':
        if sFunction == 'showEpicFavorites':
            showEpicFavorites(params)
        elif sFunction == 'openEpicFavorite':
            openEpicFavorite(params)
        elif sFunction == 'createEpicFavoriteFolder':
            createEpicFavoriteFolder(params)
        elif sFunction == 'renameEpicFavoriteFolder':
            renameEpicFavoriteFolder(params)
        elif sFunction == 'deleteEpicFavoriteFolder':
            deleteEpicFavoriteFolder(params)
        elif sFunction == 'moveEpicFavoriteEntry':
            moveEpicFavoriteEntry(params)
        elif sFunction == 'removeEpicFavoriteEntry':
            removeEpicFavoriteEntry(params)
        else:
            _endFailedDirectory()
    elif sSiteName == 'GerXStream':
        oGui = cGui()
        oGui.openSettings()
        # resolves strange errors in the logfile
        #oGui.updateDirectory()
        oGui.setEndOfDirectory()
        xbmc.executebuiltin('Action(ParentDir)')
    # Resolver Einstellungen im Hauptmenü
    elif sSiteName == 'resolver':
        oGui = cGui()
        resolver.display_settings()
        # resolves strange errors in the logfile
        oGui.setEndOfDirectory()
        xbmc.executebuiltin('Action(ParentDir)')
    # Manuelles Update im Hauptmenü
    elif sSiteName == 'devUpdates':
        from resources.lib import updateManager
        updateManager.devUpdates()
    # GerXStream aus dem installierten Kodi-Repository aktualisieren
    elif sSiteName == 'gerxstreamUpdate':
        updateGerXStream()
    # Scraper Domain-Check manuell
    elif sSiteName == 'checkDomain':
        cPluginHandler().checkDomain()
    # Plugin Infos
    elif sSiteName == 'pluginInfo':
        cPluginHandler().pluginInfo()
    # Changelog anzeigen
    elif sSiteName == 'changelog':
        from resources.lib import tools
        tools.changelog()
    # Dev Warnung anzeigen
    elif sSiteName == 'devWarning':
        from resources.lib import tools
        tools.devWarning()
    # VoD Menü Site Name
    elif sSiteName == 'vod':
        vodGuiElements(sFunction)
    # Unterordner der Einstellungen
    elif sSiteName == 'settings':
        oGui = cGui()
        for folder in settingsGuiElements():
            oGui.addFolder(folder)
        oGui.setEndOfDirectory()
    # Livestream-Bereich (Fernsehen, Sport, Social, Wetter, Webcams)
    elif sSiteName == 'livestreams':
        from resources.lib.livestreams import route as ls_route
        if sFunction == 'play':
            ls_route.play(params)
        else:
            ls_route.route(params)
    else:
        # Else load any other site as plugin and run the function
        if not _isAllowedScraperRoute(sSiteName, sFunction):
            return
        plugin = __import__(sSiteName, globals(), locals())
        function = getattr(plugin, sFunction, None)
        if not callable(function):
            _rejectPluginRoute(sSiteName, sFunction, 'function is unavailable')
            return
        function()


def showMainMenu(sFunction):
    ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')
    addon_id = cConfig().getAddonInfo('id')
    start_time = time.time()
    monitor = xbmc.Monitor()
    # timeout for the startup status check = 60s
    while (startupStatus := cCache().get(addon_id + '_main', -1)) != 'finished' and time.time() - start_time <= 60:
        if monitor.waitForAbort(1):
            return

    oGui = cGui()
    menuGroups = dict((key, []) for key in MAIN_MENU_ORDER_DEFAULT)

    oPluginHandler = cPluginHandler()
    aPlugins = oPluginHandler.getAvailablePlugins()
    if not aPlugins:
        log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: No activated Plugins found', LOGNOTICE)
        # Open the settings dialog to choose a plugin that could be enabled
        oGui.openSettings()
        oGui.updateDirectory()
    else:
        # Alle Site-Plugins erscheinen nach Inhalt statt als flache Liste.
        # Mehrfachzuordnungen sind gewollt: eine Quelle kann Filme, Serien
        # und Dokumentationen gleichzeitig anbieten.
        category_art = {
            'alle': 'all.png',
            'filme': 'movies.png',
            'serien': 'series.png',
            'animes': 'anime.png',
            'dokus': 'dokus.png',
            'kinder': 'kinder.png',
            'other': 'sources.png',
        }
        categories = oPluginHandler.getContentCategories(aPlugins)

        # "Alle" ist ein eigener Hauptordner (alle Anbieter unsortiert),
        # explizit zwischen Globaler Suche und "Filme".
        allCategory = next((entry for entry in categories if entry['id'] == 'alle'), None)
        if allCategory:
            params = ParameterHandler()
            params.setParam('category', allCategory['id'])
            oGuiElement = cGuiElement()
            oGuiElement.setTitle(allCategory['name'])
            oGuiElement.setSiteName('sourceCategory')
            oGuiElement.setFunction('showContentCategory')
            oGuiElement.setThumbnail(os.path.join(ART, category_art.get(allCategory['id'], 'categories.png')))
            menuGroups['sourceCategories'].append((oGuiElement, params))

        for category in categories:
            if category['id'] == 'alle':
                continue
            params = ParameterHandler()
            params.setParam('category', category['id'])
            oGuiElement = cGuiElement()
            oGuiElement.setTitle(category['name'])
            oGuiElement.setSiteName('sourceCategory')
            oGuiElement.setFunction('showContentCategory')
            oGuiElement.setThumbnail(os.path.join(ART, category_art.get(category['id'], 'categories.png')))
            menuGroups['sourceCategories'].append((oGuiElement, params))
    # Kategorien im Hauptmenü anzeigen. Speist sich aus TMDB und gilt damit
    # fuer alle aktivierten Quellen gleichzeitig, nicht nur fuer eine Seite.
    if cConfig().getSettingBool('showCategories', True):
        oGuiElement = cGuiElement()
        oGuiElement.setTitle(cConfig().getLocalizedString(30507))  # Kategorien
        oGuiElement.setSiteName('categories')
        oGuiElement.setFunction('categories')
        oGuiElement.setThumbnail(os.path.join(ART, 'kategorien.png'))
        menuGroups['categories'].append((oGuiElement, None))

    # Livestreams als eigener, verschiebbarer Hauptmenuepunkt. Erscheint nur,
    # wenn mindestens ein Top-Level-Bereich sichtbar ist.
    from resources.lib import contentgate
    if contentgate.get_visible_sections():
        oGuiElement = cGuiElement()
        oGuiElement.setTitle(cConfig().getLocalizedString(30989))  # Livestreams
        oGuiElement.setSiteName('livestreams')
        oGuiElement.setFunction('route')
        livestreamsArt = os.path.join(ART, 'livestreams.png')
        oGuiElement.setThumbnail(livestreamsArt if os.path.exists(livestreamsArt)
                                 else os.path.join(ART, 'sources.png'))
        menuGroups['livestreams'].append((oGuiElement, None))

    menuGroups['random'].append((randomGuiElement(), None))
    menuGroups['epicFavorites'].append((epicFavoritesGuiElement(), None))
    if cConfig().getSettingBool('watchHistoryEnabled', True):
        menuGroups['history'].append((watchHistoryGuiElement(), None))

    # VoD Ordner im Hauptmenü anzeigen
    if cConfig().getSettingBool('SettingsFolder', False):
        # Einstellung im Menü mit Untereinstellungen
        oGuiElement = cGuiElement()
        oGuiElement.setTitle(cConfig().getLocalizedString(30041))
        oGuiElement.setSiteName('settings')
        oGuiElement.setFunction('showSettingsFolder')
        oGuiElement.setThumbnail(os.path.join(ART, 'settings.png'))
        menuGroups['settings'].append((oGuiElement, None))
    else:
        for folder in settingsGuiElements():
            menuGroups['settings'].append((folder, None))
    menuGroups['globalSearch'].append((globalSearchGuiElement(), None))
    for group in _mainMenuOrder():
        for element, params in menuGroups[group]:
            if params is None:
                oGui.addFolder(element)
            else:
                oGui.addFolder(element, params)
    oGui.setEndOfDirectory()


def showContentCategory(params):
    """Zeigt die aktivierten Quellen einer Inhaltskategorie.

    Der Kategoriename kommt ausschliesslich aus cPluginHandler. Ein
    manipulierter plugin://-Parameter kann deshalb weder eine freie
    Modulbezeichnung einschleusen noch auf ein deaktiviertes Plugin zeigen.
    """
    categoryId = params.getValue('category')
    plugins = cPluginHandler().getPluginsForContentCategory(categoryId)
    oGui = cGui()
    if not plugins:
        oGui.showInfo()
        return
    for plugin in plugins:
        oGuiElement = cGuiElement()
        oGuiElement.setTitle(plugin['name'])
        oGuiElement.setSiteName(plugin['id'])
        oGuiElement.setFunction('load')
        if plugin.get('icon'):
            oGuiElement.setThumbnail(plugin['icon'])
        oGui.addFolder(oGuiElement)
    oGui.setEndOfDirectory()


def showDomainMenu(params):
    """Listet die bekannten Adressen einer Quelle zum Umschalten auf.

    Nuetzlich, wenn eine Adresse gesperrt wird (in Deutschland regelmaessig
    per DNS-Sperre): die Quelle laeuft unter einer anderen Adresse weiter,
    ohne dass der Nutzer dafuer in die Einstellungen wechseln muss.
    """
    from resources.lib import domains
    sSiteName = params.getValue('site')
    if sSiteName not in cPluginHandler().getPluginNames():
        _rejectPluginRoute(sSiteName, 'showDomains', 'site is not a scraper module')
        return
    aAlternates = domains.getAlternates(sSiteName)
    if not aAlternates:
        cGui().showInfo()
        return
    sCurrent = domains.currentDomain(sSiteName)
    oGui = cGui()
    for sDomain in aAlternates:
        # Die aktive Adresse wird markiert, sonst ist nicht erkennbar,
        # welche gerade benutzt wird.
        sTitle = ('[B]%s[/B]' % sDomain) if sDomain == sCurrent else sDomain
        oGuiElement = cGuiElement(sTitle, sSiteName, 'setSiteDomain')
        params.setParam('newDomain', sDomain)
        oGui.addFolder(oGuiElement, params)
    oGui.setEndOfDirectory()


def setSiteDomain(params):
    """Uebernimmt eine Adresse aus der hinterlegten Liste.

    Die Pruefung liegt in domains.applyDomain(): ein Wert, der nicht in der
    Liste steht, wird abgelehnt. Ein praeparierter plugin://-Link kann eine
    Quelle damit nicht auf eine fremde Adresse umbiegen (vgl. S8).
    """
    from resources.lib import domains
    sSiteName = params.getValue('site')
    if sSiteName not in cPluginHandler().getPluginNames():
        _rejectPluginRoute(sSiteName, 'setSiteDomain', 'site is not a scraper module')
        return
    sNewDomain = params.getValue('newDomain')
    if domains.applyDomain(sSiteName, sNewDomain):
        cGui().showInfo(cConfig().getLocalizedString(30835), sNewDomain)
        # Die Liste zeigt danach die neue Markierung.
        xbmc.executebuiltin('Container.Refresh')
    else:
        _rejectPluginRoute(sSiteName, 'setSiteDomain', 'domain not in allowlist')


def vodGuiElements(sFunction): # Vod Menü
    oGui = cGui()
    oPluginHandler = cPluginHandler()
    aPlugins = oPluginHandler.getAvailablePlugins() # Suche Plugins mit Pluginhandler
    if not aPlugins:
        log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: No activated Vod Plugins found', LOGNOTICE)
        # Öffne Einstellungen wenn keine VoD SitePlugins vorhanden
        oGui.openSettings()
        oGui.updateDirectory()
    else:
        # Erstelle ein gui element für alle gefundenen Siteplugins
        for aPlugin in sorted(aPlugins, key=lambda k: k['id']):
            #if cConfig().getSetting('indexVoDyes') == 'true': # Wenn VoD Menü True
            oGuiElement = cGuiElement()
            oGuiElement.setTitle(aPlugin['name'])
            oGuiElement.setSiteName(aPlugin['id'])
            if not 'vod_' in aPlugin['id']: continue # Blende alle SitePlugins ohne vod_ am Anfang aus
            oGuiElement.setFunction(sFunction)
            if 'icon' in aPlugin and aPlugin['icon']:
                oGuiElement.setThumbnail(aPlugin['icon'])
            oGui.addFolder(oGuiElement)
    oGui.setEndOfDirectory()

def settingsGuiElements():
    ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')

    # GUI GerXStream Einstellungen
    oGuiElement = cGuiElement()
    oGuiElement.setTitle(cConfig().getLocalizedString(30042))
    oGuiElement.setSiteName('GerXStream')
    oGuiElement.setFunction('display_settings')
    oGuiElement.setThumbnail(os.path.join(ART, 'gerxstream_settings.png'))
    GerXStreamSettings = oGuiElement

    # GUI Resolver Einstellungen
    oGuiElement = cGuiElement()
    oGuiElement.setTitle(cConfig().getLocalizedString(30043))
    oGuiElement.setSiteName('resolver')
    oGuiElement.setFunction('display_settings')
    oGuiElement.setThumbnail(os.path.join(ART, 'resolveurl_settings.png'))
    resolveurlSettings = oGuiElement

    # GUI Resolver-Updatemanager
    oGuiElement = cGuiElement()
    oGuiElement.setTitle(cConfig().getLocalizedString(30121))
    oGuiElement.setSiteName('devUpdates')
    oGuiElement.setFunction('devUpdates')
    oGuiElement.setThumbnail(os.path.join(ART, 'manuel_update.png'))
    ResolverUpdate = oGuiElement

    # Kodi aktualisiert GerXStream ueber das installierte Repository.
    oGuiElement = cGuiElement()
    oGuiElement.setTitle(cConfig().getLocalizedString(30902))
    oGuiElement.setSiteName('gerxstreamUpdate')
    oGuiElement.setFunction('gerxstreamUpdate')
    oGuiElement.setThumbnail(os.path.join(ART, 'manuel_update.png'))
    GerXStreamUpdate = oGuiElement

    # Sicherungen der lokalen Einstellungen, Konten und Epic-Favorites.
    oGuiElement = cGuiElement()
    oGuiElement.setTitle(cConfig().getLocalizedString(30935))
    oGuiElement.setSiteName('backup')
    oGuiElement.setFunction('showBackupMenu')
    oGuiElement.setDescription(cConfig().getLocalizedString(30936))
    oGuiElement.setThumbnail(os.path.join(ART, 'settings.png'))
    BackupRestore = oGuiElement

    # GUI Plugin Informationen
    oGuiElement = cGuiElement()
    oGuiElement.setTitle(cConfig().getLocalizedString(30267))
    oGuiElement.setSiteName('pluginInfo')
    oGuiElement.setFunction('pluginInfo')
    oGuiElement.setThumbnail(os.path.join(ART, 'plugin_info.png'))
    PluginInfo = oGuiElement

    # GUI Domain-Check der Scraper
    oGuiElement = cGuiElement()
    oGuiElement.setTitle(cConfig().getLocalizedString(30277))
    oGuiElement.setSiteName('checkDomain')
    oGuiElement.setFunction('checkDomain')
    oGuiElement.setThumbnail(os.path.join(ART, 'settings.png'))
    DomainCheck = oGuiElement
    # Reihenfolge bewusst wie im Einstellungsmenue angezeigt.
    return (GerXStreamSettings, resolveurlSettings, ResolverUpdate,
            GerXStreamUpdate, BackupRestore, PluginInfo, DomainCheck)


def showBackupMenu():
    """Show all portable-backup actions alongside the other settings tools."""
    ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')
    actions = (
        (30937, 'export', 'all'),
        (30938, 'import', 'all'),
        (30939, 'export', 'settings'),
        (30940, 'import', 'settings'),
        (30941, 'export', 'accounts'),
        (30942, 'import', 'accounts'),
        (30943, 'export', 'epic_favorites'),
        (30944, 'import', 'epic_favorites'),
    )
    oGui = cGui()
    for labelId, action, section in actions:
        element = cGuiElement(cConfig().getLocalizedString(labelId),
                              'backup', 'runBackupAction')
        element.setThumbnail(os.path.join(ART, 'settings.png'))
        actionParams = ParameterHandler()
        actionParams.setParam('action', action)
        actionParams.setParam('section', section)
        oGui.addFolder(element, actionParams)
    oGui.setEndOfDirectory()


def runBackupAction(params):
    """Perform a selected backup action and finish the transient action view."""
    from resources.lib import backup

    action = params.getValue('action')
    section = params.getValue('section')
    if action == 'export':
        backup.exportBackup(section)
    elif action == 'import':
        backup.importBackup(section)
    else:
        _rejectPluginRoute('backup', 'runBackupAction', 'unknown backup action')
        return
    cGui().setEndOfDirectory()


def globalSearchGuiElement():
    ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')

    # Create a gui element for global search
    oGuiElement = cGuiElement()
    oGuiElement.setTitle(cConfig().getLocalizedString(30040))
    oGuiElement.setSiteName('globalSearch')
    oGuiElement.setFunction('searchGlobal')
    oGuiElement.setThumbnail(os.path.join(ART, 'all.png'))
    return oGuiElement


def epicFavoritesGuiElement():
    """Main-menu entry for the user's local, nested favourites."""
    from resources.lib import epicfavorites

    ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')
    element = cGuiElement(epicfavorites.displayName(), 'epicFavorites', 'showEpicFavorites')
    element.setThumbnail(os.path.join(ART, 'all.png'))
    element.addItemProperties('epicFavoritesManaged', 'true')
    return element


def _epicContext(element, title, function, params):
    """Attach an Epic-Favorites context action to a list element."""
    context = cContextElement()
    context.setTitle(title)
    context.setFile('epicFavorites')
    context.setFunction(function)
    context.setOutputParameterHandler(params)
    element.addContextItem(context)


def _epicRefresh():
    xbmc.executebuiltin('Container.Refresh')


def _epicFolderName(default=''):
    return cGui().showKeyBoard(default, cConfig().getLocalizedString(30920))


def showEpicFavorites(params):
    """Render folders and saved plugin invocations in the chosen folder."""
    from resources.lib import epicfavorites

    requestedPath = params.getValue('path')
    path, _folder, folders, entries = epicfavorites.contents(requestedPath)
    oGui = cGui()

    # A visible action is needed for the initially empty root. The same
    # operation is also available through the long-press context menu of
    # every existing folder.
    createParams = ParameterHandler()
    createParams.setParam('path', path)
    createElement = cGuiElement(cConfig().getLocalizedString(30919),
                                'epicFavorites', 'createEpicFavoriteFolder')
    createElement.setThumbnail(os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art', 'categories.png'))
    createElement.addItemProperties('epicFavoritesManaged', 'true')
    oGui.addFolder(createElement, createParams)

    for folder in folders:
        folderPath = '/'.join(filter(None, (path, folder['id'])))
        folderParams = ParameterHandler()
        folderParams.setParam('path', folderPath)
        element = cGuiElement(folder['name'], 'epicFavorites', 'showEpicFavorites')
        element.setThumbnail(os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art', 'categories.png'))
        element.addItemProperties('epicFavoritesManaged', 'true')

        newFolderParams = ParameterHandler()
        newFolderParams.setParam('path', folderPath)
        _epicContext(element, cConfig().getLocalizedString(30919),
                     'createEpicFavoriteFolder', newFolderParams)
        renameParams = ParameterHandler()
        renameParams.setParam('path', folderPath)
        _epicContext(element, cConfig().getLocalizedString(30923),
                     'renameEpicFavoriteFolder', renameParams)
        deleteParams = ParameterHandler()
        deleteParams.setParam('path', folderPath)
        _epicContext(element, cConfig().getLocalizedString(30924),
                     'deleteEpicFavoriteFolder', deleteParams)
        oGui.addFolder(element, folderParams)

    for entry in entries:
        entryParams = ParameterHandler()
        entryParams.setParam('path', path)
        entryParams.setParam('entryId', entry['id'])
        element = cGuiElement(entry['title'], 'epicFavorites', 'openEpicFavorite')
        if entry.get('thumbnail'):
            element.setThumbnail(entry['thumbnail'])
        if entry.get('fanart'):
            element.setFanart(entry['fanart'])
        if entry.get('description'):
            element.setDescription(entry['description'])
        if entry.get('media_type'):
            element.setMediaType(entry['media_type'])
        # Gespeicherte Abspiel-Eintraege bleiben absichtlich Ordner: so
        # kann openEpicFavorite() den originalen Plugin-Aufruf unveraendert
        # ausfuehren, ohne dass Kodi vorher playMode fuer diesen Wrapper setzt.
        element.addItemProperties('epicFavoritesManaged', 'true')
        moveParams = ParameterHandler()
        moveParams.setParam('path', path)
        moveParams.setParam('entryId', entry['id'])
        _epicContext(element, cConfig().getLocalizedString(30925),
                     'moveEpicFavoriteEntry', moveParams)
        removeParams = ParameterHandler()
        removeParams.setParam('path', path)
        removeParams.setParam('entryId', entry['id'])
        _epicContext(element, cConfig().getLocalizedString(30926),
                     'removeEpicFavoriteEntry', removeParams)
        oGui.addFolder(element, entryParams, True, len(entries))

    oGui.setView('files')
    oGui.setEndOfDirectory()


def addEpicFavorite(params):
    """Add an item from any GerXStream context menu into a selected folder."""
    from resources.lib import epicfavorites

    target = params.getValue('target')
    if not target or not target.startswith('plugin://'):
        cGui().showInfo('GerXStream', cConfig().getLocalizedString(30930))
        return
    path = epicfavorites.chooseFolder()
    if path is None:
        return
    entry = {
        'title': params.getValue('title'),
        'target': target,
        'is_folder': params.getValue('isFolder') == 'true',
        'thumbnail': params.getValue('thumbnail'),
        'fanart': params.getValue('fanart'),
        'description': params.getValue('description'),
        'media_type': params.getValue('mediaType'),
    }
    stored, result = epicfavorites.addEntry(path, entry)
    if stored:
        cGui().showInfo(epicfavorites.displayName(),
                        cConfig().getLocalizedString(30928) % epicfavorites.folderTitle(path))
    elif result == 'duplicate':
        cGui().showInfo(epicfavorites.displayName(), cConfig().getLocalizedString(30929))
    else:
        cGui().showInfo(epicfavorites.displayName(), cConfig().getLocalizedString(30930))


def openEpicFavorite(params):
    """Delegate the stored item to the exact Kodi plugin URL it came from."""
    from resources.lib import epicfavorites

    entry = epicfavorites.entryAt(params.getValue('path'), params.getValue('entryId'))
    if not entry:
        _endFailedDirectory()
        return
    target = entry['target']
    if entry.get('is_folder'):
        xbmc.executebuiltin('Container.Update(%s)' % target)
    else:
        xbmc.executebuiltin('RunPlugin(%s)' % target)


def createEpicFavoriteFolder(params):
    from resources.lib import epicfavorites

    name = _epicFolderName()
    if name:
        if epicfavorites.createFolder(params.getValue('path'), name):
            _epicRefresh()
        else:
            cGui().showInfo(epicfavorites.displayName(), cConfig().getLocalizedString(30931))


def renameEpicFavoriteFolder(params):
    from resources.lib import epicfavorites

    path = params.getValue('path')
    name = _epicFolderName(epicfavorites.folderTitle(path))
    if name:
        if epicfavorites.renameFolder(path, name):
            _epicRefresh()
        else:
            cGui().showInfo(epicfavorites.displayName(), cConfig().getLocalizedString(30931))


def deleteEpicFavoriteFolder(params):
    from resources.lib import epicfavorites

    path = params.getValue('path')
    title = epicfavorites.folderTitle(path)
    if xbmcgui.Dialog().yesno(epicfavorites.displayName(),
                              cConfig().getLocalizedString(30927) % title):
        if epicfavorites.deleteFolder(path):
            _epicRefresh()


def moveEpicFavoriteEntry(params):
    from resources.lib import epicfavorites

    sourcePath = params.getValue('path')
    destinationPath = epicfavorites.chooseFolder()
    if destinationPath is None:
        return
    moved, result = epicfavorites.moveEntry(sourcePath, params.getValue('entryId'), destinationPath)
    if moved:
        _epicRefresh()
    elif result == 'duplicate':
        cGui().showInfo(epicfavorites.displayName(), cConfig().getLocalizedString(30929))


def removeEpicFavoriteEntry(params):
    from resources.lib import epicfavorites

    entry = epicfavorites.entryAt(params.getValue('path'), params.getValue('entryId'))
    if not entry:
        return
    if xbmcgui.Dialog().yesno(epicfavorites.displayName(),
                              cConfig().getLocalizedString(30927) % entry['title']):
        if epicfavorites.removeEntry(params.getValue('path'), entry['id']):
            _epicRefresh()


def randomGuiElement():
    ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')
    count = max(1, min(cConfig().getSettingInt('randomItemsCount', 250), 1000))
    title = '%s (%s)' % (cConfig().getLocalizedString(30868), count)

    oGuiElement = cGuiElement()
    oGuiElement.setTitle(title)
    oGuiElement.setSiteName('random')
    oGuiElement.setFunction('randomMovies')
    oGuiElement.setThumbnail(os.path.join(ART, 'search.png'))
    return oGuiElement


def watchHistoryGuiElement():
    ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')
    element = cGuiElement(cConfig().getLocalizedString(30903), 'history', 'showWatchHistory')
    element.setThumbnail(os.path.join(ART, 'search.png'))
    return element


def _historyTimestamp(timestamp):
    try:
        return time.strftime('%d.%m.%Y %H:%M', time.localtime(int(timestamp)))
    except (TypeError, ValueError, OverflowError):
        return ''


def showWatchHistory():
    """Render the local playback history; replay uses the normal global search."""
    from resources.lib import history

    recent = history.entries()
    oGui = cGui()
    if not recent:
        oGui.showInfo('GerXStream', cConfig().getLocalizedString(30906))
        oGui.setEndOfDirectory()
        return
    total = len(recent)
    for item in recent:
        title = item.get('title', '')
        season = item.get('season', '')
        episode = item.get('episode', '')
        if item.get('show_title') and (season or episode):
            details = 'S%sE%s' % (season or '0', episode or '0')
            title = '%s – %s: %s' % (item['show_title'], details, title)
        element = cGuiElement(title, 'history', 'resumeWatchHistory')
        mediaType = item.get('media_type', '')
        if mediaType in cGuiElement.MEDIA_TYPES:
            element.setMediaType(mediaType)
        if item.get('thumbnail'):
            element.setThumbnail(item['thumbnail'])
        description = _historyTimestamp(item.get('watched_at'))
        if item.get('source'):
            description = '%s%s' % (description, (' • ' if description else '') + item['source'])
        if description:
            element.setDescription(description)
        itemParams = ParameterHandler()
        itemParams.setParam('searchTitle', item.get('search_title', title))
        oGui.addFolder(element, itemParams, True, total)
    oGui.setView('movies')
    oGui.setEndOfDirectory()


def resumeWatchHistory(params):
    title = params.getValue('searchTitle')
    if title:
        searchGlobal(title, 'alle')
    else:
        _endFailedDirectory()


def clearWatchHistory():
    from resources.lib import history

    history.clear()
    cGui().showInfo('GerXStream', cConfig().getLocalizedString(30907))


def showRandomMovies():
    """Zeigt zufaellige TMDB-Filme, deren Klick in die globale Suche fuehrt."""
    from resources.lib.tmdb import cTMDB

    limit = max(1, min(cConfig().getSettingInt('randomItemsCount', 250), 1000))
    targetPool = max(limit * 2, 180)
    maxAttempts = 80
    extra = 'sort_by=popularity.desc&vote_count.gte=80&include_adult=false'

    tmdb = cTMDB()
    pool = []
    seenIds = set()
    attempts = 0
    while len(pool) < targetPool and attempts < maxAttempts:
        attempts += 1
        page = random.randint(1, 500)
        data = tmdb.getUrl('discover/movie', page, extra) or {}
        results = data.get('results') or []
        for item in results:
            itemId = item.get('id')
            title = item.get('title')
            if not itemId or not title or itemId in seenIds:
                continue
            seenIds.add(itemId)
            pool.append(item)

    if not pool:
        cGui().showInfo()
        return

    random.shuffle(pool)
    selected = pool[:limit]
    oGui = cGui()
    total = len(selected)
    for item in selected:
        title = item.get('title')
        if not title:
            continue

        oGuiElement = cGuiElement(title, 'random', 'searchTMDB')
        oGuiElement.setMediaType('movie')
        released = (item.get('release_date') or '')[:4]
        if released.isdigit():
            oGuiElement.setYear(released)
        if item.get('overview'):
            oGuiElement.setDescription(item['overview'])
        if item.get('poster_path'):
            oGuiElement.setThumbnail('https://image.tmdb.org/t/p/w342' + item['poster_path'])
        if item.get('backdrop_path'):
            oGuiElement.setFanart('https://image.tmdb.org/t/p/w1280' + item['backdrop_path'])

        params = ParameterHandler()
        params.setParam('searchTitle', title)
        params.setParam('searchOriginalTitle', item.get('original_title') or '')
        params.setParam('searchYear', released)
        params.setParam('searchMedia', 'movie')
        params.setParam('searchTmdbID', item.get('id'))
        oGui.addFolder(oGuiElement, params, True, total)

    oGui.setView('movies')
    oGui.setEndOfDirectory()


def showGlobalSearchMenu():
    """Globale Suche mit Filterordnern, inkl. Alle."""
    ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')
    scopes = (
        ('alle', 30857, 'all.png'),
        ('filme', 30850, 'movies.png'),
        ('serien', 30851, 'series.png'),
        ('animes', 30853, 'anime.png'),
        ('dokus', 30852, 'dokus.png'),
        ('kinder', 30854, 'kinder.png'),
    )
    oGui = cGui()
    for scope, stringId, artName in scopes:
        params = ParameterHandler()
        params.setParam('searchScope', scope)
        oGuiElement = cGuiElement(cConfig().getLocalizedString(stringId), 'globalSearch', 'searchGlobal')
        oGuiElement.setThumbnail(os.path.join(ART, artName))
        oGui.addFolder(oGuiElement, params)
    oGui.setEndOfDirectory()


def showBlockedHosterMenu():
    """Mehrfachauswahl fuer blockierte Hoster statt Freitext."""
    domains = []
    try:
        for resolverCls in resolver.relevant_resolvers(order_matters=False):
            for domain in getattr(resolverCls, 'domains', ()):
                if domain and domain not in domains:
                    domains.append(domain)
    except Exception:
        pass
    domains = sorted(domains)
    if not domains:
        xbmcgui.Dialog().ok('GerXStream', cConfig().getLocalizedString(30166) + ': keine Hosterliste verfuegbar')
        return

    selected_raw = cConfig().getSetting('blockedHoster', '')
    selected = [x.strip().lower() for x in selected_raw.replace(' ', ',').split(',') if x.strip()]
    preselect = [idx for idx, domain in enumerate(domains)
                 if domain.lower() in selected or domain.split('.')[0].lower() in selected]

    picked = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(30404), domains, preselect=preselect)
    if picked is None:
        return
    chosen = [domains[i] for i in picked]
    cConfig().setSetting('blockedHoster', ','.join(chosen))
    cGui().showInfo(cConfig().getLocalizedString(30166), '%s: %s' % (cConfig().getLocalizedString(30404), len(chosen)))


def _resolverHosterNames():
    """Namen aller ResolveURL-Hoster (ohne Debrid-/Universaldienste)."""
    names = {}
    try:
        try:
            resolvers = resolver.relevant_resolvers(include_universal=False, order_matters=False)
        except TypeError:
            resolvers = resolver.relevant_resolvers(order_matters=False)
        for resolverCls in resolvers:
            if '*' in (getattr(resolverCls, 'domains', None) or ()):
                continue  # Debrid-/Universaldienste sind keine Hoster
            name = str(getattr(resolverCls, 'name', '') or '').strip()
            if name and name.lower() not in names:
                names[name.lower()] = name
    except Exception:
        pass
    return sorted(names.values(), key=lambda value: value.casefold())


def _orderPreferredHosters(names):
    """Legt die Reihenfolge fest: zuerst gewaehlter Hoster wird zuerst probiert."""
    remaining = list(names)
    ordered = []
    while len(remaining) > 1:
        index = xbmcgui.Dialog().select(cConfig().getLocalizedString(31404) % (len(ordered) + 1), remaining)
        if index < 0:
            break
        ordered.append(remaining.pop(index))
    return ordered + remaining


def _editPreferredHosters(site, siteLabel, current):
    from resources.lib import hosterprefs

    names = hosterprefs.seenNames(site)
    if site == hosterprefs.ALL_SOURCES or len(names) < 3:
        known = set(hosterprefs.normalize(name) for name in names)
        names += [name for name in _resolverHosterNames() if hosterprefs.normalize(name) not in known]
    known = set(hosterprefs.normalize(name) for name in names)
    names = [name for name in current if hosterprefs.normalize(name) not in known] + names
    wanted = set(hosterprefs.normalize(name) for name in current)
    preselect = [index for index, name in enumerate(names) if hosterprefs.normalize(name) in wanted]
    options = names + [cConfig().getLocalizedString(31409)]
    picked = xbmcgui.Dialog().multiselect('%s: %s' % (cConfig().getLocalizedString(31401), siteLabel),
                                          options, preselect=preselect)
    if picked is None:
        return
    chosen = [names[index] for index in picked if index < len(names)]
    if len(names) in picked:
        typed = cGui().showKeyBoard('', cConfig().getLocalizedString(31409))
        if typed and hosterprefs.normalize(typed):
            chosen.append(typed.strip())
    # Bisherige Reihenfolge behalten, neue Namen hinten anhaengen.
    ordered = [name for name in current if name in chosen] + [name for name in chosen if name not in current]
    if len(ordered) > 1:
        ordered = _orderPreferredHosters(ordered)
    hosterprefs.setForSite(site, ordered)
    summary = ', '.join(ordered) if ordered else cConfig().getLocalizedString(31406)
    cGui().showInfo('GerXStream', '%s: %s' % (siteLabel, summary), 4)


def showPreferredHosterMenu():
    """Bevorzugte Hoster fuer alle Quellen oder abweichend je Quelle festlegen."""
    from resources.lib import hosterprefs

    sources = [(hosterprefs.ALL_SOURCES, cConfig().getLocalizedString(31405))]
    try:
        plugins = sorted(cPluginHandler().getAvailablePlugins(),
                         key=lambda plugin: str(plugin.get('name') or plugin.get('id')).casefold())
        for plugin in plugins:
            if plugin.get('id') and plugin.get('id') != 'livestreams':
                sources.append((plugin['id'], plugin.get('name') or plugin['id']))
    except Exception:
        logger.error('-> [gerxstream]: source list for preferred hosters unavailable')
    while True:
        data = hosterprefs.load()
        labels = []
        for site, label in sources:
            if data.get(site):
                summary = ', '.join(data[site])
            elif site == hosterprefs.ALL_SOURCES:
                summary = cConfig().getLocalizedString(31406)
            else:
                summary = cConfig().getLocalizedString(31407)
            labels.append('%s  [I]%s[/I]' % (label, summary))
        index = xbmcgui.Dialog().select(cConfig().getLocalizedString(31402), labels)
        if index < 0:
            return
        site, label = sources[index]
        _editPreferredHosters(site, label, data.get(site, []))


def showHosterGui(sFunction):
    from resources.lib.gui.hoster import cHosterGui
    if sFunction not in HOSTER_GUI_FUNCTIONS:
        _rejectPluginRoute('cHosterGui', sFunction, 'function is not allowed')
        return False
    oHosterGui = cHosterGui()
    function = getattr(oHosterGui, sFunction, None)
    if not callable(function):
        _rejectPluginRoute('cHosterGui', sFunction, 'function is unavailable')
        return False
    function()
    return True


def _runPluginSearches(searchPlugins, searchText, oGui, dialog, monitor):
    progressPlugins = max(1, len(searchPlugins))
    maxWorkers = min(6, progressPlugins)
    completed = 0
    # Eine Quelle darf die Gesamtsuche nicht dauerhaft festhalten. Der Wert
    # ist bewusst von dem HTTP-Request-Timeout getrennt konfigurierbar.
    workerTimeout = max(5, cConfig().getSettingInt('globalSearchTimeout', 30))
    futures = {}
    executor = ThreadPoolExecutor(max_workers=maxWorkers, thread_name_prefix='gerxstream-search')
    try:
        for count, pluginEntry in enumerate(searchPlugins):
            if dialog.iscanceled() or monitor.abortRequested():
                return False
            dialog.update((count + 1) * 50 // progressPlugins, cConfig().getLocalizedString(30124) + str(pluginEntry['name']) + '...')
            log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: Searching for %s at %s' % (searchText, pluginEntry['id']), LOGNOTICE)
            future = executor.submit(_pluginSearch, pluginEntry, searchText)
            futures[future] = (pluginEntry['name'], time.monotonic())

        pending = set(futures.keys())
        while pending:
            # waitForAbort(0) blocks indefinitely in Kodi 22.  This loop
            # must only test the flag; otherwise completed workers can never
            # be collected or rendered.
            if dialog.iscanceled() or monitor.abortRequested():
                for future in pending:
                    future.cancel()
                return False
            now = time.monotonic()
            expired = [future for future in pending
                       if now - futures[future][1] >= workerTimeout]
            for future in expired:
                pending.remove(future)
                future.cancel()
                completed += 1
                name = futures[future][0]
                log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: %s: search timed out after %ss' %
                    (name, workerTimeout), LOGERROR)
                dialog.update(completed * 50 // progressPlugins + 50,
                              name + cConfig().getLocalizedString(30125))
            # concurrent.futures.wait() remains asleep in Kodi 22's embedded
            # Python 3.14 although every worker has completed. Polling the
            # futures directly avoids that deadlock and still yields the GIL.
            done = {future for future in pending if future.done()}
            if not done:
                time.sleep(0.05)
                continue
            for future in done:
                pending.remove(future)
                completed += 1
                name = futures[future][0]
                try:
                    oGui.searchResults.extend(future.result() or [])
                except Exception:
                    log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: %s: collecting search results failed' % name, LOGERROR)
                dialog.update(completed * 50 // progressPlugins + 50,
                              name + cConfig().getLocalizedString(30125))
        log(cConfig().getLocalizedString(30166) +
            ' -> [gerxstream]: collected results from %s providers' % completed,
            LOGNOTICE)
        return True
    finally:
        # Bei einer defekten Quelle wird nicht auf deren Thread gewartet. Die
        # Suche kann dadurch ihre vorhandenen Ergebnisse sofort anzeigen.
        for future in futures:
            if not future.done():
                future.cancel()
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:  # Kodi-Versionen mit aelterem concurrent.futures
            executor.shutdown(wait=False)


def _collectGlobalSearchResults(searchText, includePlugin):
    from resources.lib.handler import protection

    oGui = cGui()
    monitor = xbmc.Monitor()
    oGui.globalSearch = True
    oGui._collectMode = True
    aPlugins = cPluginHandler().getAvailablePlugins()
    searchPlugins = [pluginEntry for pluginEntry in aPlugins if includePlugin(pluginEntry)]

    dialog = xbmcgui.DialogProgress()
    dialog.create(cConfig().getLocalizedString(30122), cConfig().getLocalizedString(30123))
    try:
        completed = _runPluginSearches(searchPlugins, searchText, oGui, dialog, monitor)
    finally:
        dialog.close()

    # Globale Suchen duerfen nicht durch Cloudflare-/DDoS-Hinweise in eine
    # einzelne Quelle springen. Direkt aufgerufene Quellen zeigen den Hinweis
    # weiterhin selbst; hier werden nur eventuell alte Warteschlangen geleert.
    protection.discardPendingNotifications()
    if not completed:
        oGui.setEndOfDirectory(False)
        return None

    # Manche reine Anime-Quellen liefern bei einer Suchseite die feste
    # Startseitenliste zurueck, obwohl der Begriff dort nicht vorkommt. Diese
    # Eintraege standen alphabetisch zuerst und sahen dadurch so aus, als
    # wuerde die allgemeine Suche direkt zu einem Anime-Anbieter wechseln.
    # Echte Anime-Treffer bleiben erhalten; nur nachweislich unpassende
    # Treffer aus ausschliesslichen Anime-Quellen werden entfernt.
    animeProviders = set(
        plugin['id'] for plugin in searchPlugins
        if 'animes' in plugin.get('categories', ())
        and not any(category != 'animes' for category in plugin.get('categories', ()))
    )
    searchNeedle = re.sub(r'[^a-z0-9]+', '', searchText.lower())
    searchWords = [word for word in re.findall(r'[a-z0-9]+', searchText.lower())
                   if len(word) >= 4]
    if animeProviders and (searchNeedle or searchWords):
        matchingResults = []
        discarded = 0
        for result in oGui.searchResults:
            element = result['guiElement']
            if element.getSiteName() not in animeProviders:
                matchingResults.append(result)
                continue
            resultTitle = element.getTitle().lower()
            resultNeedle = re.sub(r'[^a-z0-9]+', '', resultTitle)
            if ((searchNeedle and searchNeedle in resultNeedle)
                    or any(word in resultNeedle for word in searchWords)):
                matchingResults.append(result)
            else:
                discarded += 1
        if discarded:
            oGui.searchResults = matchingResults
            log(cConfig().getLocalizedString(30166) +
                ' -> [gerxstream]: discarded %s unrelated results from anime providers' % discarded,
                LOGNOTICE)
    log(cConfig().getLocalizedString(30166) +
        ' -> [gerxstream]: rendering %s collected search results' % len(oGui.searchResults),
        LOGNOTICE)
    return oGui


def _renderCollectedSearchResults(oGui, results=None):
    oGui._collectMode = False
    collected = oGui.searchResults if results is None else results
    total = len(collected)
    if total == 0:
        xbmcgui.Dialog().ok('GerXStream', cConfig().getLocalizedString(31622))
        oGui.setEndOfDirectory(False)
        return False
    for count, result in enumerate(sorted(collected, key=lambda k: k['guiElement'].getSiteName()), 1):
        oGui.addFolder(result['guiElement'], result['params'], bIsFolder=result['isFolder'], iTotal=total)
    oGui.setView()
    oGui.setEndOfDirectory()
    return True


def searchGlobal(sSearchText=False, scope='alle'):
    if not sSearchText:
        sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30280)) # Bitte Suchbegriff eingeben
    if not sSearchText:
        cGui().setEndOfDirectory(False)
        return False

    def _includePlugin(pluginEntry):
        if pluginEntry['globalsearch'] == 'false' or pluginEntry['globalsearch'] == '':
            return False
        if scope == 'alle':
            return True
        return scope in pluginEntry.get('categories', ())

    oGui = _collectGlobalSearchResults(sSearchText, _includePlugin)
    if oGui is None:
        return False
    return _renderCollectedSearchResults(oGui)


def searchAlter(params):
    searchTitle = params.getValue('searchTitle')
    searchImdbId = params.getValue('searchImdbID')
    searchYear = params.getValue('searchYear')
    # Wenn sYear im searchTitle vorhanden
    if ' (19' in searchTitle or ' (20' in searchTitle:
        isMatch, aYear = cParser.parse(searchTitle, r'(.*?) \((\d{4})\)')
        if isMatch:
            searchTitle = aYear[0][0]
            # Wenn kein Jahr vorhanden nutze Jahr aus searchTitle
            if searchYear is False:
                searchYear = str(aYear[0][1])
            #searchYear(aYear[0][1])
    # Wenn zusätzlich Staffel oder Episoden Markierungen im Titel sind dann abschneiden
    if ' S0' in searchTitle or ' E0' in searchTitle or ' - Staffel' in searchTitle or ' Staffel' in searchTitle:
        if ' S0' in searchTitle:
            searchTitle = searchTitle.split(' S0')[0].strip()
        elif ' E0' in searchTitle:
            searchTitle = searchTitle.split(' E0')[0].strip()
        elif ' - Staffel' in searchTitle:
            searchTitle = searchTitle.split(' - Staffel')[0].strip()
        elif ' Staffel' in searchTitle:
            searchTitle = searchTitle.split(' Staffel')[0].strip()

    oGui = _collectGlobalSearchResults(
        searchTitle,
        lambda pluginEntry: pluginEntry['globalsearch'] != 'false'
        and pluginEntry['globalsearch'] != '')
    if oGui is None:
        return False
    # check results, put this to the threaded part, too
    filteredResults = []
    for result in oGui.searchResults:
        guiElement = result['guiElement']
        log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: Site: %s Titel: %s' % (guiElement.getSiteName(), guiElement.getTitle()), LOGNOTICE)
        if searchTitle not in guiElement.getTitle():
            continue
        if guiElement._sYear and searchYear and guiElement._sYear != searchYear: continue
        if searchImdbId and guiElement.getItemProperties().get('imdbID', False) and guiElement.getItemProperties().get('imdbID', False) != searchImdbId: continue
        filteredResults.append(result)
    if not _renderCollectedSearchResults(oGui, filteredResults):
        return False
    xbmc.executebuiltin('Container.Update')
    return True


def searchTMDB(params):
    sSearchText = params.getValue('searchTitle')
    if not sSearchText:
        cGui().setEndOfDirectory(False)
        return True
    oGui = _collectGlobalSearchResults(
        sSearchText,
        lambda pluginEntry: str(pluginEntry.get('globalsearch')).lower() == 'true')
    if oGui is None:
        return False
    matching = [result for result in oGui.searchResults if _matchesSelectedTitle(result, params)]
    original = params.getValue('searchOriginalTitle')
    if not matching and original and original.casefold() != sSearchText.casefold():
        originalGui = _collectGlobalSearchResults(
            original, lambda pluginEntry: str(pluginEntry.get('globalsearch')).lower() == 'true')
        if originalGui is None:
            return False
        matching = [result for result in originalGui.searchResults if _matchesSelectedTitle(result, params)]
    if not matching:
        xbmcgui.Dialog().ok('GerXStream', cConfig().getLocalizedString(31621) % sSearchText)
        oGui.setEndOfDirectory(False)
        return False
    return _renderCollectedSearchResults(oGui, matching)


def _matchesSelectedTitle(result, params):
    import unicodedata

    def normalize(title):
        title = re.sub(r'\[(?:/?[BI]|/?COLOR[^\]]*)\]', '', str(title), flags=re.I)
        title = re.sub(r'\s*\((?:19|20)\d{2}\)\s*$', '', title)
        title = unicodedata.normalize('NFKD', title.casefold())
        return ''.join(char for char in title if char.isalnum())

    element = result['guiElement']
    title = element.getTitle()
    media = params.getValue('searchMedia')
    if media and element._mediaType and media != element._mediaType:
        return False
    properties = element.getItemProperties()
    tmdbId = params.getValue('searchTmdbID')
    resultId = properties.get('tmdbID') or element._tmdbID
    if tmdbId and resultId and str(tmdbId) != str(resultId):
        return False
    expected = {normalize(params.getValue('searchTitle'))}
    original = params.getValue('searchOriginalTitle')
    if original:
        expected.add(normalize(original))
    if not (tmdbId and resultId) and normalize(title) not in expected:
        return False
    year = params.getValue('searchYear')
    return not (year and element._sYear and str(year) != str(element._sYear))


def _pluginSearch(pluginEntry, sSearchText):
    # Nie das gemeinsame GUI-Objekt aus einem Worker veraendern: spaete oder
    # defekte Quellen koennten sonst nach dem Rendern Ergebnisse nachreichen.
    # Der Hauptthread uebernimmt die fertige Liste in _runPluginSearches().
    oGui = cGui()
    oGui.globalSearch = True
    oGui._collectMode = True
    try:
        log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: %s: search started' % pluginEntry['name'], LOGNOTICE)
        with cRequestHandler.backgroundRequests():
            plugin = __import__(pluginEntry['id'], globals(), locals())
            function = getattr(plugin, '_search')
            function(oGui, sSearchText)
        log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: %s: search finished (%s results)' %
            (pluginEntry['name'], len(oGui.searchResults)), LOGNOTICE)
        return oGui.searchResults
    except Exception:
        log(cConfig().getLocalizedString(30166) + ' -> [gerxstream]: ' + pluginEntry['name'] + ': search failed', LOGERROR)
        import traceback
        log(traceback.format_exc())
        return []


def updateGerXStream():
    """Ask Kodi to check the installed GerXStream repository now."""
    addonId = cConfig().getAddonInfo('id')
    xbmc.executebuiltin('UpdateLocalAddons()')
    xbmc.executebuiltin('UpdateAddon(%s)' % addonId)
    xbmcgui.Dialog().ok('GerXStream',
                         'Die Aktualisierung wurde im Kodi-Repository gesucht. '
                         'Bitte die Add-on-Aktualisierungen kurz abschliessen lassen.')
    return True
