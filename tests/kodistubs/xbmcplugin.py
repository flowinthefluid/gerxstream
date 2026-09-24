# -*- coding: utf-8 -*-
SORT_METHOD_UNSORTED = 0
SORT_METHOD_LABEL = 1
SORT_METHOD_VIDEO_RATING = 2
SORT_METHOD_DATE = 3
SORT_METHOD_PROGRAM_COUNT = 4
SORT_METHOD_VIDEO_RUNTIME = 5
SORT_METHOD_GENRE = 6
_ITEMS = []


def addDirectoryItem(handle, url, listitem, isFolder=False, totalItems=0):
    _ITEMS.append((url, listitem, isFolder))
    return True


def endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True):
    return None


def setResolvedUrl(handle, succeeded, listitem):
    return None


def setContent(handle, content):
    return None


def setPluginCategory(handle, category):
    return None


def addSortMethod(handle, method, *a):
    return None
