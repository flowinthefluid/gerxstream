# -*- coding: utf-8 -*-
"""Curated documentary channels; visible in Dokus, deliberately not in Alle."""
import xbmc
try:
    # Kodi's plugin loader exposes individual site modules as top-level names.
    import dokus4me as _core
except ImportError:
    # Keep the module equally importable through the normal package path used
    # by tests and static tooling.
    from sites import dokus4me as _core

SITE_IDENTIFIER = 'doku_youtube'
SITE_NAME = 'YouTube Doku-Kanaele'
SITE_ICON = 'dokus4me.png'
CONTENT_CATEGORIES = ('dokus',)
SITE_GLOBAL_SEARCH = False
ENABLE_SETTING = 'plugin_dokus4me'
INCLUDE_IN_ALL = False

def load():
    if not xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube)'):
        xbmc.executebuiltin('InstallAddon(plugin.video.youtube)')
    return _core.showSourceMenu('youtube', SITE_IDENTIFIER)

showYTChannels = _core.showYTChannels
showYTGenre = _core.showYTGenre
