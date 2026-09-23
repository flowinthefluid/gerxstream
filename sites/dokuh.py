# -*- coding: utf-8 -*-
"""Dokuh.de as an individual documentation source."""
import dokus4me as _core

SITE_IDENTIFIER = 'dokuh'
SITE_NAME = 'Dokuh.de'
SITE_ICON = 'dokus4me.png'
CONTENT_CATEGORIES = ('dokus',)
SITE_GLOBAL_SEARCH = False
ENABLE_SETTING = 'plugin_dokus4me'

def load(): return _core.showSourceMenu('dokuh', SITE_IDENTIFIER)
showEntries_3 = _core.showEntries_3
showGenre_3 = _core.showGenre_3
showHosters_3 = _core.showHosters_3
getHosterUrl_3 = _core.getHosterUrl_3
showSearch_3 = _core.showSearch_3
