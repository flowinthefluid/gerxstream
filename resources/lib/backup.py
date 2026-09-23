# -*- coding: utf-8 -*-
"""Portable, user-initiated backups for GerXStream settings and local data."""

import json
import os
import re
import time
import xml.etree.ElementTree as ElementTree

import xbmcgui
from xbmcvfs import File as VfsFile, exists as vfsExists, translatePath

from resources.lib import epicfavorites
from resources.lib.config import cConfig


FORMAT = 'gerxstream-backup'
FORMAT_VERSION = 1
SECTIONS = ('settings', 'accounts', 'epic_favorites')
ACCOUNT_GROUPS = frozenset((
    'aniworldacc', 'serienstreamacc', 'proxeracc', '2captchaacc', '9kwacc',
    'downloadplugins2', 'downloadplugins3',
))
MAX_VALUE_LENGTH = 12000
MAX_BACKUP_LENGTH = 10 * 1024 * 1024


def _text(stringId, fallback):
    value = cConfig().getLocalizedString(stringId)
    return value if value and value != str(stringId) else fallback


def _sectionName(section):
    labels = {
        'all': _text(30956, 'Complete backup'),
        'settings': _text(30953, 'Settings'),
        'accounts': _text(30954, 'Accounts'),
        'epic_favorites': _text(30955, 'Epic-Favorites'),
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
                if isAccountGroup or _looksLikeAccount(settingId):
                    accounts.add(settingId)
    return settings - accounts, accounts


def _settingValues(section):
    settingIds, accountIds = _settingIds()
    selected = accountIds if section == 'accounts' else settingIds
    config = cConfig()
    return {settingId: config.getSettingString(settingId, '')
            for settingId in sorted(selected)}


def _payload(section):
    sections = {}
    if section in ('all', 'settings'):
        sections['settings'] = _settingValues('settings')
    if section in ('all', 'accounts'):
        sections['accounts'] = _settingValues('accounts')
    if section in ('all', 'epic_favorites'):
        sections['epic_favorites'] = epicfavorites.exportData()
    return {
        'format': FORMAT,
        'format_version': FORMAT_VERSION,
        'created_at': int(time.time()),
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
        destination = VfsFile(path, 'w')
        try:
            destination.write(content)
        finally:
            destination.close()
        return True
    except (IOError, OSError, TypeError, ValueError):
        return False


def _readPayload(path):
    try:
        source = VfsFile(path)
        try:
            content = source.read()
        finally:
            source.close()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        if not isinstance(content, str) or len(content) > MAX_BACKUP_LENGTH:
            return None
        payload = json.loads(content)
    except (IOError, OSError, TypeError, ValueError):
        return None
    if (not isinstance(payload, dict) or payload.get('format') != FORMAT or
            payload.get('format_version') != FORMAT_VERSION or
            not isinstance(payload.get('sections'), dict)):
        return None
    return payload


def _requestedSections(section):
    return list(SECTIONS) if section == 'all' else [section] if section in SECTIONS else []


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
    if settings is None or accounts is None or (favorites is not None and not isinstance(favorites, dict)):
        return False
    config = cConfig()
    try:
        for settingId, value in settings.items():
            config.setSetting(settingId, value)
        for settingId, value in accounts.items():
            config.setSetting(settingId, value)
    except Exception:
        return False
    return favorites is None or epicfavorites.importData(favorites)


def exportBackup(section):
    """Ask for a target directory and create one selected backup type."""
    if section not in ('all',) + SECTIONS:
        return False
    dialog = xbmcgui.Dialog()
    title = _text(30935, 'Backup and restore')
    if section in ('all', 'accounts'):
        if not dialog.yesno(title, _text(30950,
                                         'This backup contains accounts and passwords. Store it safely.')):
            return False
    directory = dialog.browseSingle(3, _text(30945, 'Select backup folder'),
                                    'files', '', False, False, _backupDirectory())
    if not directory:
        return False
    filename = 'gerxstream-%s-%s.json' % (section, time.strftime('%Y%m%d-%H%M%S'))
    destination = os.path.join(directory, filename)
    if vfsExists(destination) and not dialog.yesno(title, _text(30957, 'Backup file already exists. Overwrite?')):
        return False
    if not _writePayload(destination, _payload(section)):
        dialog.ok(title, _text(30949, 'Invalid or unreadable backup file.'))
        return False
    dialog.ok(title, '%s:\n%s' % (_text(30947, 'Backup exported'), destination))
    return True


def importBackup(section):
    """Select, validate and apply one section from a backup file."""
    requested = _requestedSections(section)
    if not requested:
        return False
    dialog = xbmcgui.Dialog()
    title = _text(30935, 'Backup and restore')
    source = dialog.browseSingle(1, _text(30946, 'Select backup file'),
                                 'files', '.json', False, False, _backupDirectory())
    if not source:
        return False
    payload = _readPayload(source)
    if not payload:
        dialog.ok(title, _text(30949, 'Invalid or unreadable backup file.'))
        return False
    if any(item not in payload['sections'] for item in requested):
        dialog.ok(title, _text(30952, 'Backup contains no %s data.') % _sectionName(section))
        return False
    if not dialog.yesno(title, _text(30951, 'Import replaces current %s. Continue?') %
                        _sectionName(section)):
        return False
    if not _importSections(payload, requested):
        dialog.ok(title, _text(30949, 'Invalid or unreadable backup file.'))
        return False
    dialog.ok(title, _text(30948, 'Backup imported'))
    return True
