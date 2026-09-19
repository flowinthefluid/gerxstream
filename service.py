# -*- coding: utf-8 -*-
# Python 3

import os
import json
import re
import xbmc
import time

from resources.lib.config import cConfig
from resources.lib import tools
from xbmc import LOGERROR, LOGDEBUG, LOGINFO, LOGWARNING
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.handler.pluginHandler import cPluginHandler
from resources.lib import updateManager
from resources.lib.utils import translatePath
from resources.lib.tools import cCache
from resources.lib.tools import infoDialog
from resources.lib.tools import addon_log as log

MIN_RESOLVEURL_VERSION = (5, 1, 208)


# ResolverUrl Addon Data
RESOLVE_ADDON_DATA_PATH = translatePath(os.path.join('special://home/userdata/addon_data/script.module.resolveurl'))

# Pfad der update.sha
RESOLVE_SHA = os.path.join(translatePath(RESOLVE_ADDON_DATA_PATH), "update_sha")

# GerXStream Installationspfad
ADDON_PATH = translatePath(os.path.join('special://home/addons/', '%s'))

# Aktiviere GerXStream Addon
def enableAddon(ADDONID):
    struktur = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","id":1,"params": {"addonid":"%s", "properties": ["enabled"]}}' % ADDONID))
    if 'error' in struktur or struktur["result"]["addon"]["enabled"] != True:
        count = 0
        while True:
            if count == 5: break
            count += 1
            xbmc.executebuiltin('EnableAddon(%s)' % (ADDONID))
            xbmc.executebuiltin('SendClick(11)')
            xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s", "enabled":true}}' % ADDONID)
            xbmc.sleep(500)
            try:
                struktur = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","id":1,"params": {"addonid":"%s", "properties": ["enabled"]}}' % ADDONID))
                if struktur["result"]["addon"]["enabled"] == True: break
            except Exception:
                pass

# Überprüfe Abhängigkeiten
def checkDependence(ADDONID):
    isdebug = True
    if isdebug:
        log(__name__ + ' - %s - checkDependence ' % ADDONID, LOGDEBUG)
    try:
        addon_xml = os.path.join(ADDON_PATH % ADDONID, 'addon.xml')
        with open(addon_xml, 'rb') as f:
            xml = f.read()
        pattern = '(import.*?addon[^/]+)'
        allDependence = re.findall(pattern, str(xml))
        for i in allDependence:
            try:
                if 'optional' in i or 'xbmc.python' in i: continue
                pattern = 'import.*?"([^"]+)'
                IDdoADDON = re.search(pattern, i).group(1)
                if os.path.exists(ADDON_PATH % IDdoADDON) == True and not cConfig().getSettingBool('enforceUpdate', False):
                    enableAddon(IDdoADDON)
                else:
                    xbmc.executebuiltin('InstallAddon(%s)' % (IDdoADDON))
                    xbmc.executebuiltin('SendClick(11)')
                    enableAddon(IDdoADDON)
            except Exception:
                pass
    except Exception as e:
        log(__name__ + ' %s - Exception ' % e, LOGERROR)

def delHtmlCache():
    # Html Cache beim KodiStart nach (X) Tage löschen
    deltaDay = cConfig().getSettingInt('cacheDeltaDay', 2)
    deltaTime = 60*60*24*deltaDay # Tage
    currentTime = int(time.time())
    # alle x Tage
    if currentTime >= cConfig().getSettingInt('lastdelhtml', 0) + deltaTime:
        cRequestHandler('').clearCache() # Cache löschen
        cConfig().setSetting('lastdelhtml', str(currentTime))

# Zwangsupdate-Pfad: bewusst deaktiviert, solange kein eigenes Repo befuellt ist.
# Spezifikation fuer die spaetere Verdrahtung: docs/REPO-SPEC.md Abschnitt 4.


def logSelfUpdateDisabledOnce():
    setting_key = 'self_update_disabled_notice'
    if cConfig().getSettingBool(setting_key, False):
        return
    log(__name__ + ' - Selbst-Update deaktiviert, kein Repo hinterlegt', LOGINFO)
    cConfig().setSetting(setting_key, 'true')


def _parseVersionTuple(version):
    parts = re.findall(r'\d+', str(version))
    if not parts:
        return ()
    return tuple(int(part) for part in parts)


def logResolveUrlVersionStatus():
    resolve_id = 'script.module.resolveurl'
    try:
        resolve_version = cConfig(resolve_id).getAddonInfo('version')
    except Exception as e:
        log(__name__ + ' - ResolveURL-Version konnte nicht gelesen werden: %s' % e, LOGWARNING)
        return

    log(__name__ + ' - ResolveURL installiert: %s %s' % (resolve_id, resolve_version), LOGINFO)
    version_tuple = _parseVersionTuple(resolve_version)
    if version_tuple and version_tuple < MIN_RESOLVEURL_VERSION:
        minimum = '.'.join(str(part) for part in MIN_RESOLVEURL_VERSION)
        log(__name__ + ' - ResolveURL-Version unter Mindeststand %s: %s' % (minimum, resolve_version), LOGWARNING)


def main():
    tools.migrateLegacyAddonData()
    cache = cCache()
    cache_time = cConfig().getSettingInt('cacheTime', 360) * 60
    cache.clearExpired(cache_time)
    cache.set(cConfig().getAddonInfo('id') + '_main', 'running')

    logSelfUpdateDisabledOnce()
    logResolveUrlVersionStatus()

    if cConfig().getSettingBool('githubUpdateDevGerxstream', False):
        status1 = updateManager.GerXStreamDevUpdate(True)
        cRequestHandler('').clearCache()  # Cache löschen
        if cConfig().getSetting('update.notification') == 'full':  # Benachrichtung GerXStream vollständig
            infoDialog(cConfig().getLocalizedString(30112), sound=False, icon='INFO', time=10000)  # Suche Updates
            if status1 == True: infoDialog(cConfig().getLocalizedString(30113), sound=False, icon='INFO', time=6000)
            if status1 == False: infoDialog(cConfig().getLocalizedString(30114), sound=True, icon='ERROR')
            if status1 == None: infoDialog(cConfig().getLocalizedString(30115), sound=False, icon='INFO', time=6000)
        else:
            if status1 == True: infoDialog(cConfig().getLocalizedString(30113), sound=False, icon='INFO', time=6000)
            if status1 == False: infoDialog(cConfig().getLocalizedString(30114), sound=True, icon='ERROR')


    # Starte Resolver Update wenn auf Github verfügbar
    if os.path.isfile(RESOLVE_SHA) == False or cConfig().getSettingBool('githubUpdateResolver', False) or cConfig().getSettingBool('enforceUpdate', False):
        status2 = updateManager.resolverUpdate(True)
        if cConfig().getSetting('update.notification') == 'full': # Benachrichtigung Resolver vollständig
            infoDialog(cConfig().getLocalizedString(30112), sound=False, icon='INFO', time=10000)   # Suche Updates
            if status2 == True: infoDialog('Resolver ' + cConfig().getSetting('resolver.branch') + cConfig().getLocalizedString(30116), sound=False, icon='INFO', time=6000)
            if status2 == False: infoDialog(cConfig().getLocalizedString(30117), sound=True, icon='ERROR')
            if status2 == None: infoDialog(cConfig().getLocalizedString(30118), sound=False, icon='INFO', time=6000)
            if cConfig().getSettingBool('enforceUpdate', False): cConfig().setSetting('enforceUpdate', 'false')
        else:
            if status2 == True: infoDialog('Resolver ' + cConfig().getSetting('resolver.branch') + cConfig().getLocalizedString(30116), sound=False, icon='INFO', time=6000)
            if status2 == False: infoDialog(cConfig().getLocalizedString(30117), sound=True, icon='ERROR')
            if cConfig().getSettingBool('enforceUpdate', False): cConfig().setSetting('enforceUpdate', 'false')

    # Startet Überprüfung der Abhängigkeiten
    checkDependence(cConfig().getAddonInfo('id'))

    # Wenn neue settings vorhanden oder geändert in addon_data dann starte Pluginhandler und aktualisiere die PluginDB um Daten von checkDomain mit aufzunehmen
    try:
        if cConfig().getSettingBool('newSetting', False):
            cPluginHandler().getAvailablePlugins()
    except Exception:
        pass

    # getAvailablePlugins must be finished before the main menu can be started!
    cache.set(cConfig().getAddonInfo('id') + '_main', 'finished')

    # Changelog Popup in den "settings.xml" ein bzw. aus schaltbar
    if cConfig().getSettingBool('popup.update.notification', False):
        tools.changelog()

    # Html Cache beim KodiStart nach (X) Tage löschen
    delHtmlCache()

if __name__ == "__main__":
    main()