# -*- coding: utf-8 -*-
"""Portable, user-initiated backups for GerXStream settings and local data."""

import json
import os
import re
import tempfile
import time
import uuid
import xml.etree.ElementTree as ElementTree
import zipfile
from urllib.parse import unquote, urljoin, urlsplit

import xbmcgui
from xbmcvfs import File as VfsFile, exists as vfsExists, translatePath

from resources.lib import epicfavorites
from resources.lib.config import cConfig


FORMAT = 'gerxstream-backup'
FORMAT_VERSION = 1
SECTIONS = ('settings', 'accounts', 'epic_favorites', 'history', 'watched')
PORTABLE_SECTIONS = ('settings', 'epic_favorites', 'history', 'watched')
LOCAL_FILES = {'history': ('watch_history.json', []), 'watched': ('watched_items.json', {})}
ACCOUNT_GROUPS = frozenset((
    'aniworldacc', 'serienstreamacc', 'proxeracc', '2captchaacc', '9kwacc',
    'downloadplugins2', 'downloadplugins3', 'backupcloud',
))
MAX_VALUE_LENGTH = 12000
MAX_BACKUP_LENGTH = 10 * 1024 * 1024
MAX_PACKAGE_LENGTH = 100 * 1024 * 1024


def _text(stringId, fallback):
    value = cConfig().getLocalizedString(stringId)
    return value if value and value != str(stringId) else fallback


def _sectionName(section):
    labels = {
        'all': _text(30956, 'Complete backup'),
        'settings': _text(30953, 'Settings'),
        'accounts': _text(30954, 'Accounts'),
        'epic_favorites': _text(30955, 'Epic-Favorites'),
        'share': _text(31860, 'Shareable settings profile'),
        'portable': _text(31862, 'Device snapshot without accounts'),
        'history': _text(30902, 'History'),
        'watched': _text(31868, 'Watched flags'),
        'custom': _text(31884, 'Backup sections'),
    }
    return labels.get(section, section)


def _settingsPath():
    return os.path.join(translatePath(cConfig().getAddonInfo('path')),
                        'resources', 'settings.xml')


def _looksLikeAccount(settingId):
    lowered = settingId.casefold()
    sensitive_parts = ('user', 'pass', 'token', 'cookie', 'apikey', 'api_key')
    return (any(part in lowered for part in sensitive_parts) or
            lowered.endswith('bypassuseragent'))


def _settingIds():
    """Read current IDs from settings.xml; imports never write unknown IDs."""
    try:
        root = ElementTree.parse(_settingsPath()).getroot()
    except (IOError, OSError, ElementTree.ParseError):
        return set(), set()
    settings = set()
    accounts = set()
    for category in root.findall('.//category'):
        isAccountCategory = category.get('id') == 'account'
        for group in category.findall('group'):
            isAccountGroup = isAccountCategory or group.get('id') in ACCOUNT_GROUPS
            for setting in group.findall('setting'):
                settingId = setting.get('id', '')
                if not settingId or setting.get('type') == 'action':
                    continue
                settings.add(settingId)
                if (isAccountGroup or _looksLikeAccount(settingId) or
                    setting.findtext('control/hidden', '').casefold() == 'true'):
                    accounts.add(settingId)
    return settings - accounts, accounts


def _settingValues(section):
    settingIds, accountIds = _settingIds()
    selected = accountIds if section == 'accounts' else settingIds
    config = cConfig()
    return {settingId: config.getSettingString(settingId, '')
            for settingId in sorted(selected)}


def _shareSettingIds():
    settingIds, _accountIds = _settingIds()
    root = ElementTree.parse(_settingsPath()).getroot()
    allowed = {}
    for setting in root.findall('.//setting'):
        settingId = setting.get('id')
        if settingId not in settingIds or settingId in ('backupStorage', 'backupFolder'):
            continue
        options = [option.text for option in setting.findall('constraints/options/option')]
        kind = setting.get('type')
        if settingId == 'preferredHosters':
            allowed[settingId] = ('hosters', [])
        elif settingId == 'mainMenuOrder':
            allowed[settingId] = ('menu', [])
        elif kind in ('boolean', 'integer') or options:
            allowed[settingId] = (kind, options)
    return allowed


def _shareSettings():
    allowed = _shareSettingIds()
    values = _settingValues('settings')
    return {settingId: value for settingId, value in values.items()
            if settingId in allowed and _validShareValue(value, allowed[settingId])}


def _validShareValue(value, rule):
    kind, options = rule
    if not isinstance(value, str):
        return False
    if not value:
        return True
    if kind == 'menu':
        return all(item in ('epicFavorites', 'globalSearch', 'sourceCategories',
                           'categories', 'random', 'settings', 'history')
                   for item in value.split(','))
    if kind == 'hosters':
        try:
            names = json.loads(value)
        except ValueError:
            return False
        return isinstance(names, dict) and len(names) <= 100 and all(
            re.fullmatch(r'[a-zA-Z0-9_.*-]{1,80}', site) and isinstance(entries, list) and
            len(entries) <= 20 and all(isinstance(name, str) and
                                      re.fullmatch(r'[a-zA-Z0-9 _().+-]{1,60}', name)
                                      for name in entries)
            for site, entries in names.items())
    if options:
        return value in options
    if kind == 'boolean':
        return value.casefold() in ('true', 'false')
    return re.fullmatch(r'-?\d{1,10}', value) is not None


def _localPath(section):
    return os.path.join(translatePath(cConfig().getAddonInfo('profile')), LOCAL_FILES[section][0])


def _localData(section):
    _filename, empty = LOCAL_FILES[section]
    try:
        with open(_localPath(section), encoding='utf-8') as source:
            data = json.loads(source.read(MAX_BACKUP_LENGTH + 1))
        return data if _validLocalData(section, data) else empty
    except (OSError, ValueError, TypeError):
        return empty


def _validLocalData(section, data):
    if section == 'watched':
        return isinstance(data, dict) and all(
            re.fullmatch(r'[a-f0-9]{64}', key) and type(value) is int and value >= 0
            for key, value in data.items())
    if not isinstance(data, list):
        return False
    for entry in data:
        if (not isinstance(entry, dict) or not isinstance(entry.get('title'), str) or
                not entry['title'] or type(entry.get('watched_at')) is not int or
                entry['watched_at'] < 0):
            return False
        if any(not isinstance(value, (str, bool, int)) or
               (isinstance(value, str) and len(value) > MAX_VALUE_LENGTH)
               for value in entry.values()):
            return False
    return True


def _saveLocalData(section, data):
    path = _localPath(section)
    temporary = path + '.backup-import'
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(temporary, 'w', encoding='utf-8') as target:
            json.dump(data, target, ensure_ascii=False)
        os.replace(temporary, path)
        return True
    except (OSError, TypeError, ValueError):
        try:
            os.unlink(temporary)
        except OSError:
            pass
        return False


def _payload(section):
    sections = {}
    if section == 'share':
        sections['settings'] = _shareSettings()
    if section == 'portable':
        sections['settings'] = _shareSettings()
    if section in ('all', 'settings'):
        sections['settings'] = _settingValues('settings')
    if section in ('all', 'accounts'):
        sections['accounts'] = _settingValues('accounts')
    if section in ('all', 'portable', 'epic_favorites'):
        sections['epic_favorites'] = epicfavorites.exportData()
    for item in LOCAL_FILES:
        if section in ('all', 'portable', item):
            sections[item] = _localData(item)
    return {
        'format': FORMAT,
        'format_version': FORMAT_VERSION,
        'created_at': int(time.time()),
        'addon_version': cConfig().getAddonInfo('version'),
        'profile': section,
        'sections': sections,
    }


def _backupDirectory():
    directory = os.path.join(translatePath(cConfig().getAddonInfo('profile')), 'backups')
    if not os.path.isdir(directory):
        try:
            os.makedirs(directory)
        except OSError:
            return translatePath(cConfig().getAddonInfo('profile'))
    return directory


def _writePayload(path, payload):
    try:
        content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        if len(content.encode('utf-8')) > MAX_BACKUP_LENGTH:
            return False
        destination = VfsFile(path, 'w')
        try:
            return bool(destination.write(content))
        finally:
            destination.close()
    except (IOError, OSError, TypeError, ValueError):
        return False


def _readPayload(path):
    try:
        source = VfsFile(path)
        try:
            content = source.read(MAX_BACKUP_LENGTH + 1)
        finally:
            source.close()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        return _decodePayload(content)
    except (IOError, OSError, TypeError, ValueError):
        return None


def _decodePayload(content):
    try:
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_BACKUP_LENGTH:
            return None
        payload = json.loads(content)
    except (TypeError, ValueError):
        return None
    if (not isinstance(payload, dict) or payload.get('format') != FORMAT or
            payload.get('format_version') != FORMAT_VERSION or
            not isinstance(payload.get('sections'), dict)):
        return None
    return payload


def _requestedSections(section, payload=None):
    if section == 'share':
        return ['settings']
    if section == 'portable':
        return list(PORTABLE_SECTIONS)
    if section == 'all':
        requested = list(SECTIONS[:3])
        if payload:
            requested.extend(item for item in LOCAL_FILES if item in payload['sections'])
        return requested
    return [section] if section in SECTIONS else []


def _normaliseSettings(values, allowedIds):
    if not isinstance(values, dict):
        return None
    clean = {}
    for settingId, value in values.items():
        if settingId not in allowedIds or not isinstance(value, str) or len(value) > MAX_VALUE_LENGTH:
            return None
        clean[settingId] = value
    return clean


def _importSections(payload, requested):
    data = payload['sections']
    if any(section not in data for section in requested):
        return False
    settingIds, accountIds = _settingIds()
    settings = _normaliseSettings(data['settings'], settingIds) if 'settings' in requested else {}
    accounts = _normaliseSettings(data['accounts'], accountIds) if 'accounts' in requested else {}
    favorites = data.get('epic_favorites') if 'epic_favorites' in requested else None
    if (settings is None or accounts is None or
            ('epic_favorites' in requested and not isinstance(favorites, dict))):
        return False
    if payload.get('profile') == 'share':
        allowed = _shareSettingIds()
        if any(settingId not in allowed or not _validShareValue(value, allowed[settingId])
               for settingId, value in settings.items()):
            return False
    local = {section: data[section] for section in LOCAL_FILES if section in requested}
    if any(not _validLocalData(section, value) for section, value in local.items()):
        return False
    config = cConfig()
    updates = dict(settings)
    updates.update(accounts)
    previous = {settingId: config.getSettingString(settingId, '') for settingId in updates}
    previousFavorites = epicfavorites.exportData() if favorites is not None else None
    previousLocal = {section: _localData(section) for section in local}
    try:
        if favorites is not None and not epicfavorites.importData(favorites):
            return False
        for section, value in local.items():
            if not _saveLocalData(section, value):
                raise OSError('Backup section could not be saved')
        for settingId, value in updates.items():
            config.setSetting(settingId, value)
    except Exception:
        for settingId, value in previous.items():
            try:
                config.setSetting(settingId, value)
            except Exception:
                pass
        if previousFavorites is not None:
            epicfavorites.importData(previousFavorites)
        for section, value in previousLocal.items():
            _saveLocalData(section, value)
        return False
    return True


class BackupTransferError(Exception):
    pass


def _joinPath(directory, filename):
    if '://' in directory:
        return directory.rstrip('/') + '/' + filename
    return os.path.join(directory, filename)


def _storage(dialog):
    selected = cConfig().getSettingString('backupStorage', 'ask') or 'ask'
    if selected == 'ask':
        choice = dialog.select(_text(31869, 'Backup location'), [
            _text(31870, 'Folder / synchronized cloud folder'),
            _text(31871, 'Nextcloud (WebDAV)'),
        ])
        return ('folder', 'nextcloud')[choice] if choice in (0, 1) else ''
    return selected if selected in ('folder', 'nextcloud') else ''


def configureStorage():
    dialog = xbmcgui.Dialog()
    config = cConfig()
    choice = dialog.select(_text(31887, 'Configure backup location'), [
        _text(31870, 'Folder / synchronized cloud folder'),
        _text(31871, 'HTTPS-WebDAV (e.g. Nextcloud)'),
        _text(31872, 'Always ask'),
    ])
    if choice == 0:
        directory = dialog.browseSingle(3, _text(30945, 'Select backup folder'),
                                       'files', '', False, False,
                                       config.getSettingString('backupFolder', '') or _backupDirectory())
        if not directory:
            return False
        updates = {'backupFolder': directory, 'backupStorage': 'folder'}
    elif choice == 1:
        if not dialog.yesno(_text(31871, 'HTTPS-WebDAV'), _text(31889,
                'WebDAV credentials are stored locally without encryption. Use a separate app password.')):
            return False
        endpoint = dialog.input(_text(31874, 'HTTPS WebDAV folder URL'),
                                defaultt=config.getSettingString('backupCloudUrl', '')).strip()
        if not endpoint:
            return False
        try:
            _cloudUrl(endpoint=endpoint)
        except BackupTransferError:
            return _cloudFailure(dialog, _text(30935, 'Backup and restore'))
        username = dialog.input(_text(31875, 'WebDAV username'),
                                defaultt=config.getSettingString('backupCloudUser', '')).strip()
        if not username:
            return False
        password = dialog.input(_text(31876, 'WebDAV password / app password'),
                                defaultt=config.getSettingString('backupCloudPassword', ''),
                                option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not password:
            return False
        updates = {'backupCloudUrl': endpoint, 'backupCloudUser': username,
                   'backupCloudPassword': password, 'backupStorage': 'nextcloud'}
    elif choice == 2:
        updates = {'backupStorage': 'ask'}
    else:
        return False
    previous = {name: config.getSettingString(name, '') for name in updates}
    try:
        for name, value in updates.items():
            config.setSetting(name, value)
    except Exception:
        for name, value in previous.items():
            config.setSetting(name, value)
        return False
    return True


def _cloudUrl(filename='', endpoint=None):
    if endpoint is None:
        endpoint = cConfig().getSettingString('backupCloudUrl', '').strip()
    try:
        parts = urlsplit(endpoint)
        if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or
                parts.query or parts.fragment or not parts.path.startswith('/') or
                any(segment in ('.', '..') for segment in unquote(parts.path).split('/'))):
            raise ValueError()
        parts.port
    except ValueError:
        raise BackupTransferError('Invalid HTTPS WebDAV endpoint') from None
    if filename and not _backupFilename(filename):
        raise BackupTransferError('Invalid backup filename')
    return endpoint.rstrip('/') + '/' + filename


def _backupFilename(filename):
    return re.fullmatch(r'gerxstream-[a-z_]+-\d{8}-\d{6}(?:-[a-f0-9]{8})?\.(?:json|zip)', filename) is not None


def _cloudRequest(method, filename='', content=None):
    import requests

    url = _cloudUrl(filename)
    config = cConfig()
    username = config.getSettingString('backupCloudUser', '')
    password = config.getSettingString('backupCloudPassword', '')
    if not username or not password:
        raise BackupTransferError('Missing WebDAV credentials')
    requestHeaders = {'Depth': '1'} if method == 'PROPFIND' else {}
    if method == 'PUT':
        contentType = 'application/zip' if filename.endswith('.zip') else 'application/json; charset=utf-8'
        requestHeaders.update({'Content-Type': contentType,
                              'If-None-Match': '*'})
    try:
        with requests.Session() as session:
            session.trust_env = False
            with session.request(method, url, data=content, headers=requestHeaders,
                                 auth=(username, password), allow_redirects=False,
                                 verify=True, timeout=(5, 30), stream=True) as response:
                allowed = {'PUT': (201, 204), 'GET': (200,), 'PROPFIND': (207,)}
                if response.status_code not in allowed[method]:
                    raise BackupTransferError('Cloud request rejected')
                if method == 'PUT':
                    return b''
                chunks = []
                length = 0
                for chunk in response.iter_content(64 * 1024):
                    length += len(chunk)
                    if length > MAX_BACKUP_LENGTH:
                        raise BackupTransferError('Cloud response exceeds size limit')
                    chunks.append(chunk)
                return b''.join(chunks)
    except requests.RequestException:
        raise BackupTransferError('Cloud connection failed') from None


def _cloudFiles():
    endpoint = _cloudUrl()
    base = urlsplit(endpoint)
    try:
        root = ElementTree.fromstring(_cloudRequest('PROPFIND'))
    except ElementTree.ParseError:
        raise BackupTransferError('Invalid WebDAV listing') from None
    files = set()
    for response in root.findall('{DAV:}response'):
        candidate = urlsplit(urljoin(endpoint, response.findtext('{DAV:}href', '')))
        if (candidate.scheme != base.scheme or candidate.netloc != base.netloc or
                candidate.query or candidate.fragment or
                not candidate.path.startswith(base.path)):
            continue
        name = unquote(candidate.path[len(base.path):])
        if not _backupFilename(name) or not name.endswith('.json'):
            continue
        if any(prop.find('{DAV:}collection') is not None
               for prop in response.findall('.//{DAV:}resourcetype')):
            continue
        files.add(name)
    return sorted(files, reverse=True)[:200]


def _cloudFailure(dialog, title):
    dialog.ok(title, _text(31880, 'Cloud transfer failed. Check HTTPS URL, app password and permissions.'))
    return False


def _selectSections(dialog, available, importing=False):
    selected = dialog.multiselect(_text(31884, 'Backup sections'),
                                  [_sectionName(section) for section in available],
                                  preselect=[index for index, section in enumerate(available)
                                             if importing or section != 'accounts'])
    if (not isinstance(selected, list) or not selected or
            any(type(index) is not int or index < 0 or index >= len(available) for index in selected)):
        return []
    return [available[index] for index in selected]


def _selectedPayload(selected):
    if not selected or any(section not in SECTIONS for section in selected):
        raise ValueError('Invalid backup sections')
    payload = _payload('custom')
    for section in selected:
        payload['sections'].update(_payload(section)['sections'])
    return payload


def _packageAddon(target):
    root = translatePath(cConfig().getAddonInfo('path'))
    files = ['addon.xml', 'default.py', 'gerxstream.py', 'service.py', 'changelog.txt', 'license.txt']
    excluded = {'__pycache__', 'cache', 'userdata', 'backups', 'cookies'}
    extensions = {'.py', '.xml', '.json', '.po', '.png', '.jpg', '.jpeg', '.gif', '.webp',
                  '.svg', '.txt', '.ttf', '.m3u', '.m3u8'}
    for folder in ('resources', 'sites'):
        for current, directories, filenames in os.walk(os.path.join(root, folder)):
            directories[:] = [name for name in directories if not name.startswith('.') and
                              name not in excluded and not os.path.islink(os.path.join(current, name))]
            files.extend(os.path.relpath(os.path.join(current, name), root) for name in filenames
                         if not name.startswith('.') and os.path.splitext(name)[1].lower() in extensions)
    length = 0
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for filename in sorted(files):
            path = os.path.join(root, filename)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            length += os.path.getsize(path)
            if length > MAX_PACKAGE_LENGTH:
                raise BackupTransferError('Add-on package exceeds size limit')
            archive.write(path, 'plugin.video.gerxstream/' + filename.replace(os.sep, '/'))


def exportAddon():
    dialog = xbmcgui.Dialog()
    title = _text(30935, 'Backup and restore')
    storage = _storage(dialog)
    if not storage:
        return False
    directory = ''
    if storage == 'folder':
        defaultFolder = cConfig().getSettingString('backupFolder', '') or _backupDirectory()
        directory = dialog.browseSingle(3, _text(30945, 'Select backup folder'),
                                       'files', '', False, False, defaultFolder)
        if not directory:
            return False
    filename = 'gerxstream-addon-%s-%s.zip' % (time.strftime('%Y%m%d-%H%M%S'), uuid.uuid4().hex[:8])
    try:
        with tempfile.TemporaryFile(dir=_backupDirectory()) as package:
            _packageAddon(package)
            package.seek(0)
            if storage == 'nextcloud':
                _cloudRequest('PUT', filename, package)
            else:
                destination = VfsFile(_joinPath(directory, filename), 'w')
                try:
                    while True:
                        chunk = package.read(64 * 1024)
                        if not chunk:
                            break
                        if not destination.write(chunk):
                            raise OSError('Add-on package could not be written')
                finally:
                    destination.close()
    except (BackupTransferError, OSError, ValueError, TypeError, zipfile.BadZipFile):
        if storage == 'nextcloud':
            return _cloudFailure(dialog, title)
        dialog.ok(title, _text(30949, 'Invalid or unreadable backup file.'))
        return False
    dialog.ok(title, '%s:\n%s' % (_text(30947, 'Backup exported'), filename))
    return True


def exportBackup(section):
    """Ask for a target directory and create one selected backup type."""
    if section == 'addon':
        return exportAddon()
    if section not in ('all', 'share', 'portable', 'custom') + SECTIONS:
        return False
    dialog = xbmcgui.Dialog()
    title = _text(30935, 'Backup and restore')
    selected = _selectSections(dialog, list(SECTIONS)) if section == 'custom' else []
    if section == 'custom' and not selected:
        return False
    if section in ('all', 'accounts') or 'accounts' in selected:
        if not dialog.yesno(title, _text(30950,
                                         'This backup contains accounts and passwords in plaintext. Use only private storage and never share it. Continue?')):
            return False
    storage = _storage(dialog)
    if not storage:
        return False
    filename = 'gerxstream-%s-%s-%s.json' % (section, time.strftime('%Y%m%d-%H%M%S'), uuid.uuid4().hex[:8])
    payload = _selectedPayload(selected) if section == 'custom' else _payload(section)
    if storage == 'nextcloud':
        try:
            content = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            if len(content) > MAX_BACKUP_LENGTH:
                raise BackupTransferError('Backup exceeds size limit')
            _cloudRequest('PUT', filename, content)
        except (BackupTransferError, OSError, ValueError, TypeError):
            return _cloudFailure(dialog, title)
        dialog.ok(title, '%s:\n%s' % (_text(30947, 'Backup exported'), filename))
        return True
    defaultFolder = cConfig().getSettingString('backupFolder', '') or _backupDirectory()
    directory = dialog.browseSingle(3, _text(30945, 'Select backup folder'),
                                    'files', '', False, False, defaultFolder)
    if not directory:
        return False
    destination = _joinPath(directory, filename)
    if vfsExists(destination) and not dialog.yesno(title, _text(30957, 'Backup file already exists. Overwrite?')):
        return False
    if not _writePayload(destination, payload):
        dialog.ok(title, _text(30949, 'Invalid or unreadable backup file.'))
        return False
    dialog.ok(title, '%s:\n%s' % (_text(30947, 'Backup exported'), filename))
    return True


def importBackup(section):
    """Select, validate and apply one section from a backup file."""
    requested = list(SECTIONS) if section == 'custom' else _requestedSections(section)
    if not requested:
        return False
    dialog = xbmcgui.Dialog()
    title = _text(30935, 'Backup and restore')
    storage = _storage(dialog)
    if not storage:
        return False
    if storage == 'nextcloud':
        try:
            files = _cloudFiles()
            if not files:
                dialog.ok(title, _text(31881, 'No backup files found.'))
                return False
            choice = dialog.select(_text(30946, 'Select backup file'), files)
            if choice < 0 or choice >= len(files):
                return False
            payload = _decodePayload(_cloudRequest('GET', files[choice]))
        except (BackupTransferError, OSError, ValueError, TypeError):
            return _cloudFailure(dialog, title)
    else:
        defaultFolder = cConfig().getSettingString('backupFolder', '') or _backupDirectory()
        source = dialog.browseSingle(1, _text(30946, 'Select backup file'),
                                     'files', '.json', False, False, defaultFolder)
        if not source:
            return False
        payload = _readPayload(source)
    if not payload:
        dialog.ok(title, _text(30949, 'Invalid or unreadable backup file.'))
        return False
    requested = _requestedSections(section, payload)
    if section == 'custom':
        available = [item for item in SECTIONS if item in payload['sections']]
        requested = _selectSections(dialog, available, importing=True)
        if not requested:
            return False
    if section == 'share':
        payload['profile'] = 'share'
    if any(item not in payload['sections'] for item in requested):
        dialog.ok(title, _text(30952, 'Backup contains no %s data.') % _sectionName(section))
        return False
    description = ', '.join(_sectionName(item) for item in requested)
    if not dialog.yesno(title, _text(30951, 'Import replaces current %s. Continue?') % description):
        return False
    if not _importSections(payload, requested):
        dialog.ok(title, _text(30949, 'Invalid or unreadable backup file.'))
        return False
    dialog.ok(title, _text(30948, 'Backup imported'))
    return True
