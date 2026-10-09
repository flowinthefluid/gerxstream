# -*- coding: utf-8 -*-
"""Lokale, verschachtelte Favoriten fuer GerXStream.

Gespeichert werden nur der Kodi-Plugin-Aufruf und die sichtbaren Metadaten,
niemals aufgeloeste Stream- oder Hoster-URLs. Damit bleibt ein Favorit auch
bei wechselnden Hostern ein normaler GerXStream-Eintrag.
"""

import json
import os
import re
import time
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import xbmcgui
from xbmcvfs import translatePath

from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui


STORAGE_FILE = 'epic_favorites.json'
NAME_SETTING = 'epicFavoritesName'
DEFAULT_NAME = 'Epic-Watchlist'
STATUSES = ('planned', 'watching', 'completed', 'dropped')
MAX_TITLE = 300
MAX_TEXT = 2000


def displayName():
    """Return the configured, safe display name for the top-level folder."""
    name = re.sub(r'\s+', ' ', cConfig().getSetting(NAME_SETTING, DEFAULT_NAME) or '').strip()
    return DEFAULT_NAME if name in ('', 'Epic-Favorites') else name[:80]


def _profilePath():
    profile = translatePath(cConfig().getAddonInfo('profile'))
    if not os.path.isdir(profile):
        os.makedirs(profile)
    return os.path.join(profile, STORAGE_FILE)


def _emptyData():
    return {'version': 2, 'folders': [], 'entries': [], 'watchlist': []}


def normaliseTarget(target):
    if not isinstance(target, str) or not target.startswith('plugin://'):
        return ''
    parsed = urlsplit(target)
    transient = {'episodeQueue', 'episodeIndex', 'episodeStart', 'watchlistTarget',
                 'watchlistTitle', 'watchlistYear', 'watchlistIsFolder', 'manual'}
    query = [(key, value) for key, value in parse_qsl(parsed.query)
             if key not in transient]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ''))


def _clean(value, maximum=MAX_TEXT):
    if not isinstance(value, str):
        value = str(value or '')
    return re.sub(r'\s+', ' ', value).strip()[:maximum]


def seriesName(title):
    title = _clean(title, MAX_TITLE)
    cleaned = re.sub(r'[\s._-]*S\d{1,3}\s*E\d{1,3}\s*(?=\(\d{4}\)\s*$|$)',
                     ' ', title, flags=re.IGNORECASE).strip()
    return cleaned or title


def _cleanNode(node):
    """Validate a persisted folder recursively and discard malformed fields."""
    if not isinstance(node, dict):
        return None
    folderId = str(node.get('id') or '')
    if not re.fullmatch(r'[a-f0-9]{8,32}', folderId):
        return None
    cleaned = {
        'id': folderId,
        'name': _clean(node.get('name'), 100),
        'folders': [],
        'entries': [],
    }
    if not cleaned['name']:
        return None
    for child in node.get('folders', []):
        valid = _cleanNode(child)
        if valid:
            cleaned['folders'].append(valid)
    for entry in node.get('entries', []):
        valid = _cleanEntry(entry)
        if valid:
            cleaned['entries'].append(valid)
    return cleaned


def _cleanEntry(entry):
    if not isinstance(entry, dict):
        return None
    target = normaliseTarget(entry.get('target'))
    entryId = str(entry.get('id') or '')
    if not re.fullmatch(r'[a-f0-9]{8,32}', entryId) or not target.startswith('plugin://'):
        return None
    title = _clean(entry.get('title'), MAX_TITLE)
    if entry.get('media_type') == 'tvshow':
        title = seriesName(title)
    if not title:
        return None
    return {
        'id': entryId,
        'title': title,
        'target': target[:12000],
        'is_folder': bool(entry.get('is_folder')),
        'thumbnail': _clean(entry.get('thumbnail'), MAX_TEXT),
        'fanart': _clean(entry.get('fanart'), MAX_TEXT),
        'description': _clean(entry.get('description'), MAX_TEXT),
        'media_type': entry.get('media_type') if entry.get('media_type') in
                      ('movie', 'tvshow', 'season', 'episode') else '',
        'added_at': int(entry.get('added_at') or 0),
        'source': _clean(entry.get('source'), 100),
        'year': _clean(entry.get('year'), 10),
        'series_title': _clean(entry.get('series_title'), MAX_TITLE),
        'series_target': normaliseTarget(entry.get('series_target')),
        'status': entry.get('status') if entry.get('status') in STATUSES else '',
    }


def _normaliseData(raw):
    """Return a safe Epic-Favorites tree, suitable for imported data too."""
    if not isinstance(raw, dict):
        return _emptyData()
    data = _emptyData()
    for folder in raw.get('folders', []):
        valid = _cleanNode(folder)
        if valid:
            data['folders'].append(valid)
    for entry in raw.get('entries', []):
        valid = _cleanEntry(entry)
        if valid:
            data['entries'].append(valid)
    storedWatchlist = raw.get('watchlist', [])
    for entry in storedWatchlist if isinstance(storedWatchlist, list) else []:
        valid = _cleanEntry(entry)
        if valid and valid['status']:
            data['watchlist'].append(valid)
    return data


def _load():
    try:
        with open(_profilePath(), 'r', encoding='utf-8') as handle:
            raw = json.load(handle)
    except (IOError, OSError, ValueError, TypeError):
        return _emptyData()
    return _normaliseData(raw)


def _save(data):
    path = _profilePath()
    temporary = path + '.new'
    try:
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(',', ':'))
        os.replace(temporary, path)
        return True
    except (IOError, OSError, TypeError, ValueError):
        try:
            if os.path.exists(temporary):
                os.unlink(temporary)
        except OSError:
            pass
    return False


def exportData():
    """Return a validated, JSON-serialisable snapshot of all Epic-Favorites."""
    return _load()


def importData(data):
    """Replace Epic-Favorites with a validated backup snapshot."""
    if (not isinstance(data, dict) or not isinstance(data.get('folders'), list) or
            not isinstance(data.get('entries'), list)):
        return False
    return _save(_normaliseData(data))


def _pathParts(path):
    return [part for part in str(path or '').split('/')
            if re.fullmatch(r'[a-f0-9]{8,32}', part)]


def normalisePath(path):
    return '/'.join(_pathParts(path))


def _folder(data, path):
    current = data
    for folderId in _pathParts(path):
        current = next((item for item in current.get('folders', [])
                        if item.get('id') == folderId), None)
        if current is None:
            return None
    return current


def _folderLabel(data, path):
    names = []
    current = data
    for folderId in _pathParts(path):
        current = next((item for item in current.get('folders', [])
                        if item.get('id') == folderId), None)
        if not current:
            break
        names.append(current['name'])
    return ' / '.join(names) or displayName()


def contents(path=''):
    """Return ``(canonical_path, folder, folders, entries)`` for rendering."""
    data = _load()
    parts = _pathParts(path)
    node = _folder(data, '/'.join(parts))
    if node is None:
        parts = []
        node = data
    return '/'.join(parts), node, list(node['folders']), list(node['entries'])


def createFolder(path, name):
    name = _clean(name, 100)
    if not name:
        return False
    data = _load()
    parent = _folder(data, path)
    if parent is None:
        return False
    if any(item['name'].casefold() == name.casefold() for item in parent['folders']):
        return False
    parent['folders'].append({'id': uuid.uuid4().hex, 'name': name,
                              'folders': [], 'entries': []})
    return _save(data)


def renameFolder(path, name):
    name = _clean(name, 100)
    parts = _pathParts(path)
    if not name or not parts:
        return False
    data = _load()
    parent = _folder(data, '/'.join(parts[:-1]))
    node = _folder(data, '/'.join(parts))
    if parent is None or node is None:
        return False
    if any(item is not node and item['name'].casefold() == name.casefold()
           for item in parent['folders']):
        return False
    node['name'] = name
    return _save(data)


def deleteFolder(path):
    parts = _pathParts(path)
    if not parts:
        return False
    data = _load()
    parent = _folder(data, '/'.join(parts[:-1]))
    if parent is None:
        return False
    previous = len(parent['folders'])
    parent['folders'] = [item for item in parent['folders'] if item['id'] != parts[-1]]
    return previous != len(parent['folders']) and _save(data)


def addEntry(path, entry):
    data = _load()
    parent = _folder(data, path)
    if parent is None:
        return False, 'invalid'
    clean = _cleanEntry(dict(entry, id=uuid.uuid4().hex, added_at=int(time.time())))
    if not clean:
        return False, 'invalid'
    if any(item['target'] == clean['target'] for item in parent['entries']):
        return False, 'duplicate'
    parent['entries'].append(clean)
    return (_save(data), 'saved')


def removeEntry(path, entryId):
    data = _load()
    parent = _folder(data, path)
    if parent is None:
        return False
    previous = len(parent['entries'])
    parent['entries'] = [item for item in parent['entries'] if item['id'] != entryId]
    return previous != len(parent['entries']) and _save(data)


def moveEntry(sourcePath, entryId, destinationPath):
    data = _load()
    source = _folder(data, sourcePath)
    destination = _folder(data, destinationPath)
    if source is None or destination is None or source is destination:
        return False, 'invalid'
    entry = next((item for item in source['entries'] if item['id'] == entryId), None)
    if entry is None:
        return False, 'invalid'
    if any(item['target'] == entry['target'] for item in destination['entries']):
        return False, 'duplicate'
    source['entries'] = [item for item in source['entries'] if item['id'] != entryId]
    destination['entries'].append(entry)
    return (_save(data), 'saved')


def entryAt(path, entryId):
    """Return one stored entry or ``None`` without exposing the storage tree."""
    data = _load()
    folder = _folder(data, path)
    if folder is None:
        return None
    return next((entry for entry in folder['entries'] if entry['id'] == entryId), None)


def chooseFolder(startPath='', allowCreate=True):
    """Controller-friendly picker: save here, descend, go back, create."""
    path = normalisePath(startPath)
    dialog = xbmcgui.Dialog()
    while True:
        data = _load()
        node = _folder(data, path)
        if node is None:
            path = ''
            node = data
        entries = [(cConfig().getLocalizedString(30921) % _folderLabel(data, path), 'save')]
        if path:
            entries.append((cConfig().getLocalizedString(30932), 'back'))
        if allowCreate:
            entries.append((cConfig().getLocalizedString(30919), 'create'))
        entries.extend((folder['name'], folder['id']) for folder in node['folders'])
        choice = dialog.select('%s: %s' % (displayName(), _folderLabel(data, path)),
                               [entry[0] for entry in entries])
        if choice < 0:
            return None
        action = entries[choice][1]
        if action == 'save':
            return path
        if action == 'back':
            path = '/'.join(_pathParts(path)[:-1])
            continue
        if action == 'create':
            name = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30920))
            if name and createFolder(path, name):
                data = _load()
                parent = _folder(data, path)
                created = next((folder for folder in parent['folders']
                                if folder['name'].casefold() == _clean(name, 100).casefold()), None)
                if created:
                    path = '/'.join(filter(None, (path, created['id'])))
            continue
        path = '/'.join(filter(None, (path, action)))


def folderTitle(path=''):
    return _folderLabel(_load(), path)


def seriesEntry(entry):
    values = dict(entry)
    values['title'] = _clean(values.get('title'), MAX_TITLE)
    if not values['title']:
        return None
    if values.get('media_type') in ('episode', 'season'):
        if not values.get('series_target') or not values.get('series_title'):
            return None
        values.update(title=values['series_title'], target=values['series_target'],
                      media_type='tvshow', is_folder=True)
    if values.get('media_type') == 'tvshow':
        values['title'] = seriesName(values['title'])
        values['series_title'] = seriesName(values.get('series_title') or values['title'])
    target = normaliseTarget(values.get('target'))
    if not target:
        return None
    route = dict(parse_qsl(urlsplit(target).query))
    values['source'] = route.get('site', '') or values.get('source', '')
    values['target'] = target
    if re.fullmatch(r'\d{4}', str(values.get('year') or '')) and not re.search(r'\(\d{4}\)', values['title']):
        values['title'] += ' (%s)' % values['year']
    return values


def targetForEntry(entry):
    target = normaliseTarget(entry.get('series_target') or entry.get('target'))
    if not target.startswith('plugin://plugin.video.gerxstream/') or not entry.get('media_type'):
        return target
    parsed = urlsplit(target)
    query = dict(parse_qsl(parsed.query))
    title = entry.get('series_title') or entry.get('show_title') or entry['title']
    year = entry.get('year') or ''
    match = re.search(r'\((\d{4})\)\s*$', title)
    if match and not year:
        year = match.group(1)
    query.update(watchlistTarget=target, watchlistTitle=title, watchlistYear=year,
                 watchlistIsFolder=str(bool(entry.get('is_folder'))).lower())
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ''))


def _watchKey(entry):
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', entry['title']).casefold().strip()
    year = entry.get('year') or ''
    match = re.search(r'\((\d{4})\)\s*$', entry['title'])
    if not year and match:
        year = match.group(1)
    kind = 'tvshow' if entry.get('media_type') in ('tvshow', 'season', 'episode') else 'movie'
    return title, year, kind


def watchEntries(status):
    return [entry for entry in sorted(_load()['watchlist'],
                                     key=lambda item: item['added_at'], reverse=True)
            if entry['status'] == status]


def watchEntry(entryId):
    return next((entry for entry in _load()['watchlist'] if entry['id'] == entryId), None)


def setStatus(entry, status, automatic=False):
    if status not in STATUSES:
        return False
    values = seriesEntry(entry)
    if values is None:
        return False
    data = _load()
    previous = next((item for item in data['watchlist'] if _watchKey(item) == _watchKey(values)), None)
    if previous:
        entryId = previous['id']
        if automatic and previous['status'] in ('completed', 'dropped'):
            status = previous['status']
    else:
        entryId = uuid.uuid4().hex
    clean = _cleanEntry(dict(values, id=entryId, status=status, added_at=int(time.time())))
    if not clean:
        return False
    data['watchlist'] = [clean] + [item for item in data['watchlist'] if item['id'] != entryId]
    return _save(data)


def removeWatchEntry(entryId):
    data = _load()
    previous = len(data['watchlist'])
    data['watchlist'] = [entry for entry in data['watchlist'] if entry['id'] != entryId]
    return len(data['watchlist']) != previous and _save(data)
