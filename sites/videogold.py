# -*- coding: utf-8 -*-
"""VideoGold as an individual documentation source."""
import dokus4me as _core

SITE_IDENTIFIER = 'videogold'
SITE_NAME = 'VideoGold'
SITE_ICON = 'dokus4me.png'
CONTENT_CATEGORIES = ('dokus',)
SITE_GLOBAL_SEARCH = False
ENABLE_SETTING = 'plugin_dokus4me'

def load(): return _core.showSourceMenu('videogold', SITE_IDENTIFIER)
showDoku_6 = _core.showDoku_6
showThemen_6 = _core.showThemen_6
showEntries_6 = _core.showEntries_6
showHosters_6 = _core.showHosters_6
getHosterUrl_6 = _core.getHosterUrl_6
showSearch_6 = _core.showSearch_6
