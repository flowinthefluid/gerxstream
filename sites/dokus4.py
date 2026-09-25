# -*- coding: utf-8 -*-
"""Dokus4.me as an individual documentation source."""
import dokus4me as _core

SITE_IDENTIFIER = 'dokus4'
SITE_NAME = 'Dokus4.me'
SITE_ICON = 'dokus4me.png'
CONTENT_CATEGORIES = ('dokus',)
SITE_GLOBAL_SEARCH = False
ENABLE_SETTING = 'plugin_dokus4me'

def load(): return _core.showSourceMenu('dokus4', SITE_IDENTIFIER)
showEntries_1 = _core.showEntries_1
showGenre_1 = _core.showGenre_1
showHosters_1 = _core.showHosters_1
getHosterUrl_1 = _core.getHosterUrl_1
showSearch_1 = _core.showSearch_1
