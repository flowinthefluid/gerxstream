# -*- coding: utf-8 -*-
"""Minimaler xbmc-Stub fuer Unit-Tests ausserhalb von Kodi."""
LOGDEBUG = 0
LOGINFO = 1
LOGNOTICE = 1
LOGWARNING = 3
LOGERROR = 4
LOGFATAL = 6

_LOG = []


def log(msg, level=LOGDEBUG):
    _LOG.append((level, msg))


def getInfoLabel(_label):
    return ''


def getCondVisibility(_cond):
    return False


def executebuiltin(_cmd):
    return None


def sleep(_ms):
    return None


def translatePath(path):
    return path


class Monitor(object):
    def abortRequested(self):
        return False

    def waitForAbort(self, _timeout=0):
        return False


class Player(object):
    def play(self, *a, **k):
        return None

    def isPlayingVideo(self):
        return False

    def getTime(self):
        return 0

    def getTotalTime(self):
        return 0


class PlayList(object):
    def __init__(self, *a, **k):
        pass

    def clear(self):
        pass

    def add(self, *a, **k):
        pass


PLAYLIST_VIDEO = 1


class Keyboard(object):
    def __init__(self, *a, **k):
        pass


class Actor(object):
    def __init__(self, *a, **k):
        pass
