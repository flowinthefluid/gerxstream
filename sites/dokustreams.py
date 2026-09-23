# -*- coding: utf-8 -*-
"""Dokustreams.de as an individual documentation source."""
import dokus4me as _core

SITE_IDENTIFIER = 'dokustreams'
SITE_NAME = 'Dokustreams.de'
SITE_ICON = 'dokus4me.png'
CONTENT_CATEGORIES = ('dokus',)
SITE_GLOBAL_SEARCH = False
ENABLE_SETTING = 'plugin_dokus4me'

def load(): return _core.showSourceMenu('dokustreams', SITE_IDENTIFIER)
showEntries_2 = _core.showEntries_2
showGenre_2 = _core.showGenre_2
showEpisodes_2 = _core.showEpisodes_2
showHosters_2 = _core.showHosters_2
getHosterUrl_2 = _core.getHosterUrl_2
showSearch_2 = _core.showSearch_2
