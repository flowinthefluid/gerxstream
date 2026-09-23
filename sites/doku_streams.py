# -*- coding: utf-8 -*-
"""Doku-Streams.com as an individual documentation source."""
import dokus4me as _core

SITE_IDENTIFIER = 'doku_streams'
SITE_NAME = 'Doku-Streams.com'
SITE_ICON = 'dokus4me.png'
CONTENT_CATEGORIES = ('dokus',)
SITE_GLOBAL_SEARCH = False
ENABLE_SETTING = 'plugin_dokus4me'

def load(): return _core.showSourceMenu('doku_streams', SITE_IDENTIFIER)
showEntries_4 = _core.showEntries_4
showGenre_4 = _core.showGenre_4
showHosters_4 = _core.showHosters_4
getHosterUrl_4 = _core.getHosterUrl_4
showSearch_4 = _core.showSearch_4
