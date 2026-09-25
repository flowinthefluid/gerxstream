# -*- coding: utf-8 -*-
"""Curated documentary channels; visible in Dokus, deliberately not in Alle."""
import xbmc
import dokus4me as _core

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
showYTLists = _core.showYTLists
showYTMore = _core.showYTMore
showYTSearch = _core.showYTSearch
