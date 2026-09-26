# -*- coding: utf-8 -*-
NOTIFICATION_INFO = 'info'
_WIN_PROPS = {}


class Window(object):
    def __init__(self, _wid=0):
        pass

    def getProperty(self, key):
        return _WIN_PROPS.get(key, '')

    def setProperty(self, key, value):
        _WIN_PROPS[key] = value

    def clearProperty(self, key):
        _WIN_PROPS.pop(key, None)


class ListItem(object):
    def __init__(self, label='', path=''):
        self._label = label
        self._path = path
        self._props = {}
        self._art = {}

    def setProperty(self, k, v):
        self._props[k] = v

    def getPath(self):
        return self._path

    def setArt(self, art):
        self._art.update(art)

    def setMimeType(self, _m):
        pass

    def setContentLookup(self, _b):
        pass

    def getVideoInfoTag(self):
        return _VTag()


class _VTag(object):
    def __getattr__(self, _name):
        return lambda *a, **k: None


class Dialog(object):
    def ok(self, *a, **k):
        return True

    def select(self, *a, **k):
        return -1

    def multiselect(self, *a, **k):
        return None

    def notification(self, *a, **k):
        return None

    def textviewer(self, *a, **k):
        return None
