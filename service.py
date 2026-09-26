# -*- coding: utf-8 -*-
# Python 3

import json
import os
import re
import time

import xbmc

from xbmc import LOGDEBUG, LOGERROR, LOGINFO, LOGWARNING
from resources.lib import tools
from resources.lib.config import cConfig
from resources.lib.handler.pluginHandler import cPluginHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import addon_log as log
from resources.lib.tools import cCache
from resources.lib.utils import translatePath


MIN_RESOLVEURL_VERSION = (5, 1, 209)
ADDON_PATH = translatePath(os.path.join('special://home/addons/', '%s'))


def enableAddon(addon_id):
    status = json.loads(xbmc.executeJSONRPC(
        '{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","id":1,'
        '"params":{"addonid":"%s","properties":["enabled"]}}' % addon_id))
    if 'error' not in status and status['result']['addon']['enabled']:
        return

    for _ in range(5):
        xbmc.executebuiltin('EnableAddon(%s)' % addon_id)
        xbmc.executebuiltin('SendClick(11)')
        xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,'
            '"params":{"addonid":"%s","enabled":true}}' % addon_id)
        xbmc.sleep(500)
        try:
            status = json.loads(xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","id":1,'
                '"params":{"addonid":"%s","properties":["enabled"]}}' % addon_id))
            if status['result']['addon']['enabled']:
                return
        except Exception:
            pass


def checkDependence(addon_id):
    log('%s - %s - checkDependence' % (__name__, addon_id), LOGDEBUG)
    try:
        addon_xml = os.path.join(ADDON_PATH % addon_id, 'addon.xml')
        with open(addon_xml, 'rb') as addon_file:
            dependencies = re.findall(r'import.*?addon[^/]+', str(addon_file.read()))
        for dependency in dependencies:
            try:
                if 'optional' in dependency or 'xbmc.python' in dependency:
                    continue
                dependency_id = re.search(r'import.*?"([^"]+)', dependency).group(1)
                if os.path.exists(ADDON_PATH % dependency_id):
                    enableAddon(dependency_id)
                else:
                    xbmc.executebuiltin('InstallAddon(%s)' % dependency_id)
                    xbmc.executebuiltin('SendClick(11)')
                    enableAddon(dependency_id)
            except Exception:
                pass
    except Exception as exc:
        log('%s - dependency check failed: %s' % (__name__, exc), LOGERROR)


def delHtmlCache():
    delta_day = int(cConfig().getSetting('cacheDeltaDay', 2))
    current_time = int(time.time())
    if current_time >= int(cConfig().getSetting('lastdelhtml', 0)) + (60 * 60 * 24 * delta_day):
        cRequestHandler('').clearCache()
        cConfig().setSetting('lastdelhtml', str(current_time))


def logRepositoryUpdatesOnce():
    setting_key = 'repository_update_notice'
    if not cConfig().getSettingBool(setting_key, False):
        log('%s - Updates werden über das installierte Kodi-Repository bezogen' % __name__, LOGINFO)
        cConfig().setSetting(setting_key, 'true')


def logResolveUrlVersionStatus():
    resolve_id = 'script.module.resolveurl'
    try:
        resolve_version = cConfig(resolve_id).getAddonInfo('version')
    except Exception as exc:
        log('%s - ResolveURL-Version konnte nicht gelesen werden: %s' % (__name__, exc), LOGWARNING)
        return

    log('%s - ResolveURL installiert: %s %s' % (__name__, resolve_id, resolve_version), LOGINFO)
    version_tuple = tuple(int(part) for part in re.findall(r'\d+', str(resolve_version)))
    if version_tuple and version_tuple < MIN_RESOLVEURL_VERSION:
        minimum = '.'.join(str(part) for part in MIN_RESOLVEURL_VERSION)
        log('%s - ResolveURL-Version unter Mindeststand %s: %s' %
            (__name__, minimum, resolve_version), LOGWARNING)


def main():
    tools.migrateLegacyAddonData()
    cache = cCache()
    cache.clearExpired(cConfig().getSettingInt('cacheTime', 360) * 60)
    cache.set(cConfig().getAddonInfo('id') + '_main', 'running')

    logRepositoryUpdatesOnce()
    logResolveUrlVersionStatus()
    checkDependence(cConfig().getAddonInfo('id'))

    try:
        if cConfig().getSettingBool('newSetting', False):
            cPluginHandler().getAvailablePlugins()
    except Exception:
        pass

    cache.set(cConfig().getAddonInfo('id') + '_main', 'finished')
    if cConfig().getSettingBool('popup.update.notification', False):
        tools.changelog()
    delHtmlCache()

    # Livestream-Listen (M3U + EPG) fuer den IPTV Simple Client erzeugen.
    # Baut hoechstens alle N Stunden neu und wirft nie - ein Fehler hier darf
    # den Kodi-Start nicht stoeren.
    # Pluto-TV-Senderliste (offizielle, anonyme Schnittstelle) auffrischen.
    try:
        if cConfig().getSettingBool('lsPlutoEnabled', True):
            from resources.lib.livestreams.providers import pluto
            pluto.refresh()
    except Exception as exc:
        log('%s - Pluto-TV-Aktualisierung uebersprungen: %s' % (__name__, exc), LOGWARNING)

    try:
        from resources.lib.livestreams import export as livestreams_export
        livestreams_export.refresh()
    except Exception as exc:
        log('%s - Livestream-Export uebersprungen: %s' % (__name__, exc), LOGWARNING)


if __name__ == '__main__':
    main()
