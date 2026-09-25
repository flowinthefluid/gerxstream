# -*- coding: utf-8 -*-
"""xbmcaddon-Stub mit einem gemeinsamen, prozessweiten Settings-Speicher."""
import os

_STORE = {}   # addon_id -> {setting_id: str}

_INFO_DEFAULTS = {
    'id': 'plugin.video.gerxstream',
    'name': 'GerXStream',
    'version': '1.0.27',
    'profile': os.environ.get('GXS_PROFILE', '/tmp/gxs-test-profile'),
    'path': os.environ.get('GXS_ADDON_PATH', os.getcwd()),
    'fanart': '',
    'icon': '',
}


def _reset():
    _STORE.clear()


class Addon(object):
    def __init__(self, addon_id='plugin.video.gerxstream'):
        self._id = addon_id
        _STORE.setdefault(addon_id, {})

    def getSetting(self, sid):
        return _STORE[self._id].get(sid, '')

    def setSetting(self, sid, value):
        _STORE[self._id][sid] = '' if value is None else str(value)

    def getSettingBool(self, sid):
        return str(_STORE[self._id].get(sid, '')).lower() in ('true', '1', 'yes', 'on')

    def getSettingInt(self, sid):
        try:
            return int(_STORE[self._id].get(sid, 0))
        except (TypeError, ValueError):
            return 0

    def getAddonInfo(self, key):
        if self._id == 'plugin.video.gerxstream':
            return _INFO_DEFAULTS.get(key, '')
        return {'id': self._id, 'version': '0', 'profile': _INFO_DEFAULTS['profile']}.get(key, '')

    def getLocalizedString(self, sid):
        return '#%s' % sid

    def openSettings(self):
        return None
