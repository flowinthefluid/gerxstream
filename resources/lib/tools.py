# -*- coding: utf-8 -*-
# Python 3

import xbmc
import xbmcgui
import hashlib
import json
import re
import os
import time
import shutil

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib import pyaes
from resources.lib.config import cConfig
from xbmcvfs import translatePath
from urllib.parse import quote, unquote, quote_plus, unquote_plus, urlparse
from html.entities import name2codepoint
from difflib import SequenceMatcher
from functools import lru_cache
from os import path, chdir

LEGACY_ADDON_ID = 'plugin.video.xstream'
CURRENT_ADDON_ID = 'plugin.video.gerxstream'
ADDON_DATA_MIGRATION_MARKER = '.gerxstream_data_migrated'
LEGACY_INSTALL_HINT_MARKER = '.gerxstream_legacy_install_hint_shown'


def _addonDataPath(addon_id):
    return translatePath(os.path.join('special://home/userdata/addon_data', addon_id))


def _writeMarker(marker_path, content):
    try:
        marker_dir = os.path.dirname(marker_path)
        if marker_dir and not os.path.isdir(marker_dir):
            os.makedirs(marker_dir)
        with open(marker_path, mode='w', encoding='utf-8') as marker_file:
            marker_file.write(content)
    except Exception as e:
        log('[tools] Failed to write marker %s: %s' % (marker_path, e), LOGERROR)


def migrateLegacyAddonData():
    addon_id = cConfig().getAddonInfo('id')
    if addon_id != CURRENT_ADDON_ID:
        return False

    old_data_path = _addonDataPath(LEGACY_ADDON_ID)
    new_data_path = _addonDataPath(CURRENT_ADDON_ID)
    marker_path = os.path.join(new_data_path, ADDON_DATA_MIGRATION_MARKER)

    if os.path.isfile(marker_path):
        return False

    copied_files = 0
    os.makedirs(new_data_path, exist_ok=True)

    if os.path.isdir(old_data_path):
        for src_root, _, file_names in os.walk(old_data_path):
            rel_path = os.path.relpath(src_root, old_data_path)
            dst_root = new_data_path if rel_path == '.' else os.path.join(new_data_path, rel_path)
            os.makedirs(dst_root, exist_ok=True)
            for file_name in file_names:
                src_file = os.path.join(src_root, file_name)
                dst_file = os.path.join(dst_root, file_name)
                if os.path.exists(dst_file):
                    continue
                try:
                    shutil.copy2(src_file, dst_file)
                    copied_files += 1
                except Exception as e:
                    log('[tools] Could not migrate %s: %s' % (src_file, e), LOGERROR)

    marker_content = 'migrated_from=%s\ntime=%s\nfiles=%s\n' % (
        LEGACY_ADDON_ID,
        int(time.time()),
        copied_files)
    _writeMarker(marker_path, marker_content)
    if copied_files:
        log('[tools] Migrated %s addon_data files from %s to %s' % (copied_files, LEGACY_ADDON_ID, CURRENT_ADDON_ID), LOGDEBUG)
    return copied_files > 0


def showLegacyInstallHintOnce():
    addon_id = cConfig().getAddonInfo('id')
    if addon_id != CURRENT_ADDON_ID:
        return

    addon_data_path = _addonDataPath(CURRENT_ADDON_ID)
    marker_path = os.path.join(addon_data_path, LEGACY_INSTALL_HINT_MARKER)
    if os.path.isfile(marker_path):
        return

    legacy_addon_path = translatePath(os.path.join('special://home/addons', LEGACY_ADDON_ID))
    if not os.path.isdir(legacy_addon_path):
        return

    xbmcgui.Dialog().ok(
        cConfig().getAddonInfo('name'),
        'Alte Installation erkannt: plugin.video.xstream.\n'
        'Dieses Addon verwendet jetzt plugin.video.gerxstream.\n'
        'Bitte entferne die alte Installation, um Doppelinstallationen zu vermeiden.')
    _writeMarker(marker_path, 'shown=%s\n' % int(time.time()))

# Aufgeführte Plattformen zum Anzeigen der Systemplattform
def platform():
    if xbmc.getCondVisibility('system.platform.android'):
        return 'Android'
    elif xbmc.getCondVisibility('system.platform.linux'):
        return 'Linux'
    elif xbmc.getCondVisibility('system.platform.linux.Raspberrypi'):
        return 'Linux/RPi'
    elif xbmc.getCondVisibility('system.platform.windows'):
        return 'Windows'
    elif xbmc.getCondVisibility('system.platform.uwp'):
        return 'Windows UWP'      
    elif xbmc.getCondVisibility('system.platform.osx'):
        return 'OSX'
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return 'ATV2'
    elif xbmc.getCondVisibility('system.platform.ios'):
        return 'iOS'
    elif xbmc.getCondVisibility('system.platform.darwin'):
        return 'iOS'
    elif xbmc.getCondVisibility('system.platform.xbox'):
        return 'XBOX'
    elif xbmc.getCondVisibility('System.HasAddon(service.coreelec.settings)'):
        return 'CoreElec'
    elif xbmc.getCondVisibility('System.HasAddon(service.libreelec.settings)'):
        return 'LibreElec'
    elif xbmc.getCondVisibility('System.HasAddon(service.osmc.settings)'):
        return 'OSMC'


# zeigt nach Update den Changelog als Popup an
def changelog():
    addon_path = translatePath(cConfig().getAddonInfo('path'))
    CHANGELOG_PATH = os.path.join(addon_path, 'changelog.txt')
    version = cConfig().getAddonInfo('version')
    if cConfig().getSetting('changelog_version') == version or not os.path.isfile(CHANGELOG_PATH):
        return
    cConfig().setSetting('changelog_version', version)
    heading = cConfig().getLocalizedString(30275)
    with open(CHANGELOG_PATH, mode='r', encoding='utf-8') as f:
        cl_lines = f.readlines()
    announce = ''
    for line in cl_lines:
        announce += line
    textBox(heading, announce)


# zeigt die Entwickler Optionen Warnung als Popup an
def devWarning():
    addon_path = translatePath(cConfig().getAddonInfo('path'))
    POPUP_PATH = os.path.join(addon_path, 'resources', 'popup', 'devWarning.txt')
    heading = cConfig().getLocalizedString(30322)
    with open(POPUP_PATH, mode='r', encoding='utf-8') as f:
        cl_lines = f.readlines()
    announce = ''
    for line in cl_lines:
        announce += line
    textBox(heading, announce)


# Erstellt eine Textbox
def textBox(heading, announce):
    text = announce
    if isinstance(announce, str) and os.path.isfile(announce):
        try:
            with open(announce, mode='r', encoding='utf-8') as text_file:
                text = text_file.read()
        except Exception:
            text = announce
    xbmcgui.Dialog().textviewer(heading, str(text))


# Info Meldung im Kodi
def infoDialog(message, heading=None, icon='', time=5000, sound=False):
    if heading is None:
        heading = cConfig().getAddonInfo('name')
    if icon == '': icon = cConfig().getAddonInfo('icon')
    elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
    elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
    elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
    xbmcgui.Dialog().notification(heading, message, icon, time, sound=sound)


class cParser:
    @staticmethod
    def _get_compiled_pattern(pattern, flags=0):
        return re.compile(pattern, flags)
    
    @staticmethod
    def _replaceSpecialCharacters(s):
        try:
            # Umlaute Unicode konvertieren
            for t in (('\\/', '/'), ('&amp;', '&'), ('\\u00c4', 'Ä'), ('\\u00e4', 'ä'),
                ('\\u00d6', 'Ö'), ('\\u00f6', 'ö'), ('\\u00dc', 'Ü'), ('\\u00fc', 'ü'),
                ('\\u00df', 'ß'), ('\\u2013', '-'), ('\\u00b2', '²'), ('\\u00b3', '³'),
                ('\\u00e9', 'é'), ('\\u2018', '‘'), ('\\u201e', '„'), ('\\u201c', '“'),
                ('\\u00c9', 'É'), ('\\u2026', '...'), ('\\u202f', 'h'), ('\\u2019', '’'),
                ('\\u0308', '̈'), ('\\u00e8', 'è'), ('#038;', ''), ('\\u00f8', 'ø'),
                ('／', '/'), ('\\u00e1', 'á'), ('&#8211;', '-'), ('&#8220;', '“'), ('&#8222;', '„'),
                ('&#8217;', '’'), ('&#8230;', '…'), ('\\u00bc', '¼'), ('\\u00bd', '½'), ('\\u00be', '¾'),
                ('\\u2153', '⅓'), ('\\u002A', '*')):
                s = s.replace(*t)

            # Umlaute HTML konvertieren
            for h in (('\\/', '/'), ('&#x26;', '&'), ('&#039;', "'"), ("&#39;", "'"),
                ('&#xC4;', 'Ä'), ('&#xE4;', 'ä'), ('&#xD6;', 'Ö'), ('&#xF6;', 'ö'),
                ('&#xDC;', 'Ü'), ('&#xFC;', 'ü'), ('&#xDF;', 'ß') , ('&#xB2;', '²'),
                ('&#xDC;', '³'), ('&#xBC;', '¼'), ('&#xBD;', '½'), ('&#xBE;', '¾'),
                ('&#8531;', '⅓'), ('&#8727;', '*')):
                s = s.replace(*h)
        except Exception:
            pass
        return s

    @staticmethod
    def parseSingleResult(sHtmlContent, pattern, ignoreCase=False):
        if sHtmlContent:
            flags = re.S | re.M
            if ignoreCase:
                flags |= re.I

            matches = cParser._get_compiled_pattern(pattern, flags).search(sHtmlContent)
            
            if matches:
                # Check if there's at least one capturing group
                if matches.lastindex is not None and matches.lastindex >= 1:
                    return True, cParser._replaceSpecialCharacters(matches.group(1))
                else:
                    # fallback to the entire match if no group was captured
                    return True, cParser._replaceSpecialCharacters(matches.group(0))
        return False, None
    
    @staticmethod
    def parse(sHtmlContent, pattern, iMinFoundValue=1, ignoreCase=False):
        if sHtmlContent:
            flags = re.DOTALL
            if ignoreCase:
                flags |= re.I

            aMatches = cParser._get_compiled_pattern(pattern, flags).findall(sHtmlContent)
            
            if len(aMatches) >= iMinFoundValue:
                # handle both single strings and tuples of matches
                if isinstance(aMatches[0], tuple):
                    # Process each string in tuple
                    aMatches = [tuple(cParser._replaceSpecialCharacters(x) if isinstance(x, str) and x is not None else '' for x in match) for match in aMatches]
                else:
                    # Process single strings
                    aMatches = [cParser._replaceSpecialCharacters(x) if isinstance(x, str) and x is not None else '' for x in aMatches]
                
                return True, aMatches
        return False, None

    @staticmethod
    def replace(pattern, sReplaceString, sValue):
        return cParser._get_compiled_pattern(pattern).sub(sReplaceString, sValue)

    @staticmethod
    def search(pattern, sValue, ignoreCase=True):
        flags = 0
        if ignoreCase:
            flags = re.IGNORECASE
        return cParser._get_compiled_pattern(pattern, flags).search(sValue)

    @staticmethod
    def escape(sValue):
        return re.escape(sValue)

    @staticmethod
    def getNumberFromString(sValue):
        aMatches = re.compile(r'\d+').findall(sValue)
        if len(aMatches) > 0:
            return int(aMatches[0])
        return 0

    @staticmethod
    def urlparse(sUrl):
        return urlparse(sUrl.replace('www.', '')).netloc.title()

    @staticmethod
    def urlDecode(sUrl):
        return unquote(sUrl)

    @staticmethod
    def urlEncode(sUrl, safe=''):
        return quote(sUrl, safe)

    @staticmethod
    def quote(sUrl):
        return quote(sUrl)

    @staticmethod
    def unquotePlus(sUrl):
        return unquote_plus(sUrl)

    @staticmethod
    def quotePlus(sUrl):
        return quote_plus(sUrl)

    @staticmethod
    def B64decode(text):
        import base64
        return base64.b64decode(text).decode('utf-8')


# xStream interner Log
class logger:
    @staticmethod
    def info(sInfo):
        logger.__writeLog(sInfo, cLogLevel=xbmc.LOGINFO)

    @staticmethod
    def debug(sInfo):
        logger.__writeLog(sInfo, cLogLevel=xbmc.LOGDEBUG)

    @staticmethod
    def warning(sInfo):
        logger.__writeLog(sInfo, cLogLevel=xbmc.LOGWARNING)

    @staticmethod
    def error(sInfo):
        logger.__writeLog(sInfo, cLogLevel=xbmc.LOGERROR)

    @staticmethod
    def fatal(sInfo):
        logger.__writeLog(sInfo, cLogLevel=xbmc.LOGFATAL)

    @staticmethod
    def __writeLog(sLog, cLogLevel=xbmc.LOGDEBUG):
        params = ParameterHandler()
        try:
            if params.exist('site'):
                site = params.getValue('site')
                sLog = "[%s] -> [%s]: %s" % (cConfig().getAddonInfo('name'), site, sLog)
            else:
                sLog = "[%s] %s" % (cConfig().getAddonInfo('name'), sLog)
            xbmc.log(sLog, cLogLevel)
        except Exception as e:
            xbmc.log('Logging Failure: %s' % e, cLogLevel)
            pass


class cUtil:
    @staticmethod
    def removeHtmlTags(sValue, sReplace=''):
        return re.compile(r'<.*?>').sub(sReplace, sValue)

    @staticmethod
    def unescape(text):
        # edit kasi 2024-11-26 so für py2/py3 oder für nur py3 unichr ersetzen durch chr
        try: unichr
        except NameError: unichr = chr

        def fixup(m):
            text = m.group(0)
            if not text.endswith(';'): text += ';'
            if text[:2] == '&#':
                try:
                    if text[:3] == '&#x':
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                try:
                    text = unichr(name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text

        if isinstance(text, str):
            try:
                text = text.decode('utf-8')
            except Exception:
                try:
                    text = text.decode('utf-8', 'ignore')
                except Exception:
                    pass
        return re.compile('&(\\w+;|#x?\\d+;?)').sub(fixup, text.strip())

    @staticmethod
    def cleanse_text(text):
        if text is None: text = ''
        text = cUtil.removeHtmlTags(text)
        return text

    @staticmethod
    def evp_decode(cipher_text, passphrase, salt=None):
        if not salt:
            salt = cipher_text[8:16]
            cipher_text = cipher_text[16:]
        key, iv = cUtil.evpKDF(passphrase, salt)
        decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(key, iv))
        plain_text = decrypter.feed(cipher_text)
        plain_text += decrypter.feed()
        return plain_text.decode("utf-8")

    @staticmethod
    def evpKDF(pwd, salt, key_size=32, iv_size=16):
        temp = b''
        fd = temp
        while len(fd) < key_size + iv_size:
            h = hashlib.md5()
            h.update(temp + pwd + salt)
            temp = h.digest()
            fd += temp
        key = fd[0:key_size]
        iv = fd[key_size:key_size + iv_size]
        return key, iv
        
    @staticmethod
    def isSimilar(sSearch, sText, threshold=0.9):
        return (SequenceMatcher(None, sSearch, sText).ratio() >= threshold)

    @staticmethod
    @lru_cache(maxsize=200000)
    def get_seq_match_ratio(token1, token2):
        return SequenceMatcher(None, token1, token2).ratio()
    
    @staticmethod
    def isSimilarByToken(sSearch, sText, threshold=0.9):
        tokens_sSearch = sSearch.split()
        tokens_sText = sText.split()

        if not tokens_sSearch:
            return False

            # get_ratio = lambda a, b: SequenceMatcher(None, a, b).ratio()
        best_ratios = [
            max(cUtil.get_seq_match_ratio(token, token2) for token2 in tokens_sText)
            for token in tokens_sSearch
        ]
        return (sum(best_ratios) / len(best_ratios)) >= threshold

def valid_email(email): #ToDo: Funktion in Settings / Konten aktivieren
    # Überprüfen der EMail-Adresse mit dem Muster
    if re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$').match(email):
        return True
    else:
        return False

def getDNS(dns):
    status = 'Beschäftigt'
    loop = 1
    while status == 'Beschäftigt':
        if loop == 20:
            break
        status = xbmc.getInfoLabel(dns)
        xbmc.sleep(20)
        loop += 1
    return status

def getRepofromAddonsDB(addonID):
    from sqlite3 import dbapi2 as database
    from glob import glob
    chdir(path.join(translatePath('special://database/')))
    addonsDB = path.join(translatePath('special://database/'), sorted(glob("Addons*.db"), reverse=True)[0])
    dbcon = database.connect(addonsDB)
    dbcur = dbcon.cursor()
    select = ("SELECT origin FROM installed WHERE addonID = '%s'") % addonID
    dbcur.execute(select)
    match = dbcur.fetchone()
    dbcon.close()
    if match and len(match) > 0:
         repo = match[0]
    else:
        repo = ''
    return repo


class cCache(object):
    MAX_ENTRIES = 200
    _win = None

    def __init__(self):
        # see https://kodi.wiki/view/Window_IDs
        self._win = xbmcgui.Window(10000)
        addon_id = cConfig().getAddonInfo('id') or CURRENT_ADDON_ID
        self._property_prefix = addon_id + '.volatileCache.'
        self._registry_property = self._property_prefix + 'registry'

    def __del__(self):
        del self._win

    def _entryProperty(self, key):
        return self._property_prefix + 'entry.' + str(key)

    def _getRegistry(self):
        registry_data = self._win.getProperty(self._registry_property)
        if not registry_data:
            return {}
        try:
            registry = json.loads(registry_data)
        except (TypeError, ValueError):
            self._win.clearProperty(self._registry_property)
            return {}
        if not isinstance(registry, dict):
            self._win.clearProperty(self._registry_property)
            return {}

        valid_registry = {}
        for key, timestamp in registry.items():
            if not isinstance(key, str):
                continue
            try:
                valid_registry[key] = float(timestamp)
            except (TypeError, ValueError):
                continue
        return valid_registry

    def _setRegistry(self, registry):
        if registry:
            self._win.setProperty(self._registry_property, json.dumps(registry, separators=(',', ':')))
        else:
            self._win.clearProperty(self._registry_property)

    def _removeEntry(self, key, registry):
        self._win.clearProperty(self._entryProperty(key))
        registry.pop(key, None)

    def _readEntry(self, key):
        cache_data = self._win.getProperty(self._entryProperty(key))
        if not cache_data:
            return None
        try:
            timestamp, data = json.loads(cache_data)
            return float(timestamp), data
        except (TypeError, ValueError):
            return None

    def _limitEntries(self, registry):
        while len(registry) > self.MAX_ENTRIES:
            oldest_key = min(registry, key=registry.get)
            self._removeEntry(oldest_key, registry)

    def get(self, key, cache_time):
        key = str(key)
        registry = self._getRegistry()
        if key not in registry:
            self._win.clearProperty(self._entryProperty(key))
            return None
        cache_data = self._readEntry(key)

        if cache_data:
            if time.time() - cache_data[0] < cache_time or cache_time < 0:
                return cache_data[1]
        self._removeEntry(key, registry)
        self._setRegistry(registry)

        return None

    def set(self, key, data):
        key = str(key)
        timestamp = time.time()
        try:
            cache_data = json.dumps((timestamp, data), separators=(',', ':'))
        except (TypeError, ValueError):
            return

        registry = self._getRegistry()
        self._win.setProperty(self._entryProperty(key), cache_data)
        registry[key] = timestamp
        self._limitEntries(registry)
        self._setRegistry(registry)

    def clearExpired(self, cache_time):
        if cache_time < 0:
            return

        registry = self._getRegistry()
        current_time = time.time()
        for key in list(registry):
            cache_data = self._readEntry(key)
            if not cache_data or current_time - cache_data[0] >= cache_time:
                self._removeEntry(key, registry)
        self._setRegistry(registry)

    def clear(self):
        registry = self._getRegistry()
        for key in registry:
            self._win.clearProperty(self._entryProperty(key))
        self._win.clearProperty(self._registry_property)
