# -*- coding: utf-8 -*-
"""Cross-invocation playback context and persistent watched flags."""

import hashlib
import json
import math
import os
import re
import time
import uuid

import xbmc
import xbmcgui
from xbmcvfs import translatePath

from resources.lib.config import cConfig
from resources.lib.episodequeue import EPISODE_PLAYLIST_PROPERTY


PLAYBACK_PROPERTY = 'GerXStream.PlaybackContext'
WATCHED_PERCENT = 90
WATCHED_FILE = 'watched_items.json'


def _clean(value):
    return ' '.join(str(value or '').split()).casefold()


def _number(value):
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return _clean(value)


def itemKey(source, title, season='', episode='', showTitle='', contentId=''):
    if not title:
        return ''
    if showTitle and str(season or '') and str(episode or ''):
        identity = [_clean(source), _clean(showTitle), _number(season), _number(episode)]
    else:
        identity = [_clean(source), _clean(title), str(contentId or '')]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=True).encode('utf-8')).hexdigest()


def _validKey(key):
    return isinstance(key, str) and re.fullmatch(r'[a-f0-9]{64}', key) is not None


class WatchedStore:
    def __init__(self, path=None):
        self.path = path or os.path.join(
            translatePath(cConfig().getAddonInfo('profile')), WATCHED_FILE)
        self._signature = None
        self._entries = {}

    def _load(self):
        try:
            status = os.stat(self.path)
            signature = (status.st_mtime_ns, status.st_size)
            if signature != self._signature:
                with open(self.path, encoding='utf-8') as handle:
                    entries = json.load(handle)
                self._entries = entries if isinstance(entries, dict) else {}
                self._signature = signature
        except (OSError, ValueError, TypeError):
            self._entries = {}
            self._signature = None
        return self._entries

    def contains(self, key):
        return _validKey(key) and key in self._load()

    def mark(self, key):
        if not _validKey(key):
            return False
        entries = dict(self._load())
        entries[key] = int(time.time())
        temporary = self.path + '.new'
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(temporary, 'w', encoding='utf-8') as handle:
                json.dump(entries, handle, separators=(',', ':'))
            os.replace(temporary, self.path)
            self._signature = None
            return True
        except (OSError, ValueError, TypeError):
            try:
                os.unlink(temporary)
            except OSError:
                pass
            return False


_watched = WatchedStore()


def isWatched(key):
    return _watched.contains(key)


def beginPlayback(data, params):
    key = params.getValue('watchId')
    if not _validKey(key):
        key = itemKey(params.getValue('site'), data.get('title'),
                      params.getValue('season'), params.getValue('episode'),
                      data.get('showTitle'), params.getValue('sUrl'))
    hasNext = None
    if params.getValue('episodeQueue'):
        from resources.lib import episodequeue
        targets = episodequeue.getTargets(params.getValue('episodeQueue'))
        try:
            index = int(params.getValue('episodeIndex'))
            if 0 <= index < len(targets):
                hasNext = index < len(targets) - 1
        except (TypeError, ValueError):
            pass
    context = {
        'token': uuid.uuid4().hex,
        'watch_id': key,
        'stream': str(data.get('link') or '').partition('|')[0],
        'playlist': xbmcgui.Window(10000).getProperty(EPISODE_PLAYLIST_PROPERTY),
        'has_next': hasNext,
        'history': {
            'title': data.get('title', ''), 'thumbnail': data.get('thumb', ''),
            'mediaType': params.getValue('mediaType') or 'movie',
            'source': params.getValue('site') or '', 'season': params.getValue('season') or '',
            'episode': params.getValue('episode') or '', 'showTitle': data.get('showTitle') or '',
            'target': params.getValue('watchlistTarget') or '',
            'targetIsFolder': params.getValue('watchlistIsFolder') == 'true',
            'seriesTarget': params.getValue('watchlistTarget') or '',
            'seriesTitle': params.getValue('watchlistTitle') or data.get('showTitle') or '',
            'year': params.getValue('watchlistYear') or '',
        },
    }
    xbmcgui.Window(10000).setProperty(PLAYBACK_PROPERTY, json.dumps(context))
    return key


class PlaybackMonitor(xbmc.Player):
    def __init__(self, store=None):
        super().__init__()
        self.store = store or WatchedStore()
        self.context = None
        self.playedTime = 0
        self.totalTime = 0
        self.marked = False

    def _pendingContext(self):
        try:
            value = json.loads(xbmcgui.Window(10000).getProperty(PLAYBACK_PROPERTY))
            if (isinstance(value, dict) and isinstance(value.get('stream'), str)
                    and value['stream'] and isinstance(value.get('token'), str)
                    and value['token'] and _validKey(value.get('watch_id'))):
                return value
            return None
        except (ValueError, TypeError):
            return None

    def _markProgress(self):
        if (self.context and not self.marked and self.totalTime > 0
                and math.isfinite(self.totalTime) and math.isfinite(self.playedTime)
                and self.playedTime / self.totalTime >= WATCHED_PERCENT / 100.0):
            self.marked = self.store.mark(self.context.get('watch_id'))

    def tick(self):
        try:
            if not self.isPlayingVideo():
                if self.context:
                    self._finish(not self._hasFollowingEpisode())
                return
            stream = self.getPlayingFile().partition('|')[0]
            pending = self._pendingContext()
            playingKey = ''
            if not pending or pending['stream'] != stream:
                try:
                    playingKey = self.getVideoInfoTag().getUniqueID('gerxstream')
                except (AttributeError, RuntimeError):
                    pass
            if (_validKey(playingKey)
                    and (not pending or pending['watch_id'] != playingKey)):
                pending = {'token': 'tag:' + playingKey, 'watch_id': playingKey,
                           'stream': stream, 'playlist': ''}
            if pending and (pending['stream'] == stream or pending['watch_id'] == playingKey):
                if not self.context or pending['token'] != self.context['token']:
                    pending['stream'] = stream
                    self.context = pending
                    self.playedTime = 0
                    self.totalTime = 0
                    self.marked = self.store.contains(pending.get('watch_id'))
                    from resources.lib import history
                    if pending.get('history'):
                        try:
                            history.record(**pending['history'])
                        except (OSError, RuntimeError, TypeError, ValueError):
                            pass
            if self.context and self.context['stream'] == stream:
                self.playedTime = self.getTime()
                self.totalTime = self.getTotalTime()
                self._markProgress()
            elif self.context:
                self._finish(False)
        except (RuntimeError, ValueError, TypeError):
            return

    def onAVStarted(self):
        self.tick()
        if self.context and not xbmc.getCondVisibility('Window.IsActive(FullScreenVideo)'):
            xbmc.executebuiltin('ActivateWindow(FullScreenVideo)', True)

    def onPlayBackSeek(self, position, seekOffset):
        if self.context:
            self.playedTime = position / 1000.0
            self._markProgress()

    def _finish(self, clearPlaylist):
        self._markProgress()
        if self.context:
            window = xbmcgui.Window(10000)
            pending = self._pendingContext()
            if pending and pending.get('token') == self.context['token']:
                window.clearProperty(PLAYBACK_PROPERTY)
            if (clearPlaylist and self.context.get('playlist')
                    and window.getProperty(EPISODE_PLAYLIST_PROPERTY) == self.context['playlist']):
                window.clearProperty(EPISODE_PLAYLIST_PROPERTY)
                from resources.lib import hosterprefs
                hosterprefs.forgetSticky()
        self.context = None

    def onPlayBackStopped(self):
        self._finish(True)

    def _hasFollowingEpisode(self):
        if self.context and isinstance(self.context.get('has_next'), bool):
            return self.context['has_next']
        try:
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            return playlist.getposition() < playlist.size() - 1
        except Exception:
            return False

    def onPlayBackEnded(self):
        self._markProgress()
        if not self.isPlayingVideo():
            self._finish(not self._hasFollowingEpisode())

    def onPlayBackError(self):
        self._finish(True)

    def run(self):
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            self.tick()
            if monitor.waitForAbort(0.5):
                break