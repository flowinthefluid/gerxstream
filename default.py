# -*- coding: utf-8 -*-
# Python 3

def main():
    from gerxstream import parseUrl
    from os.path import join
    from sys import path
    import platform

    from resources.lib.config import cConfig
    from resources.lib import tools
    from xbmc import LOGINFO as LOGNOTICE, log
    from xbmcvfs import translatePath

    _addonPath_ = translatePath(cConfig().getAddonInfo('path'))
    path.append(join(_addonPath_, 'resources', 'lib'))
    path.append(join(_addonPath_, 'resources', 'lib', 'gui'))
    path.append(join(_addonPath_, 'resources', 'lib', 'handler'))
    path.append(join(_addonPath_, 'resources', 'art', 'sites'))
    path.append(join(_addonPath_, 'resources', 'art'))
    path.append(join(_addonPath_, 'sites'))    
    
    LOGMESSAGE = cConfig().getLocalizedString(30166)
    log('-----------------------------------------------------------------------', LOGNOTICE)
    log(LOGMESSAGE + ' -> [default]: Start GerXStream Log, Version %s ' % cConfig().getAddonInfo('version'), LOGNOTICE)
    log(LOGMESSAGE + ' -> [default]: Python-Version: %s' % platform.python_version(), LOGNOTICE)

    tools.migrateLegacyAddonData()
    tools.showLegacyInstallHintOnce()

    try:
        parseUrl()
    except Exception as e:
        if str(e) == 'UserAborted':
            log(LOGMESSAGE + ' -> [default]: User aborted list creation', LOGNOTICE)
        else:
            import traceback
            import xbmcgui
            log(traceback.format_exc(), LOGNOTICE)
            # Die technische Ausnahme steht vollstaendig im Kodi-Protokoll.
            # Im Fernseher-Dialog hilft ein abgeschnittener Python-Trace nicht
            # weiter und verdeckt die eigentliche Bedienung der Quelle.
            message = ('Die Quelle konnte nicht verarbeitet werden.\n\n'
                       'Technischer Grund: %s\n\n'
                       'Details stehen im Kodi-Protokoll.') % e.__class__.__name__
            xbmcgui.Dialog().ok('GerXStream', message)

if __name__ == "__main__":
    main()
