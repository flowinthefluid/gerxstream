import json
import io
import zipfile

import pytest

from resources.lib import backup
from resources.lib.config import cConfig
from conftest import set_setting


def test_share_profile_contains_no_accounts_or_device_paths(monkeypatch):
    set_setting('autoNextEpisodeEnabled', 'true')
    set_setting('preferedQuality', '5')
    set_setting('epicFavoritesName', 'Family')
    set_setting('serienstreamPassword', 'private-password')
    set_setting('downloadpath', 'smb://user:password@server/private')
    monkeypatch.setattr(backup.epicfavorites, 'exportData', lambda: {'version': 2})
    payload = backup._payload('share')
    assert set(payload['sections']) == {'settings'}
    settings = payload['sections']['settings']
    assert settings['autoNextEpisodeEnabled'] == 'true'
    assert settings['preferedQuality'] == '5'
    assert 'downloadpath' not in settings
    assert 'serienstreamPassword' not in settings
    assert 'private-password' not in json.dumps(payload)
    assert 'smb://' not in json.dumps(payload)


def test_share_profile_rejects_secrets_in_structured_values():
    set_setting('autoNextEpisodeEnabled', 'secret-cookie')
    set_setting('preferedQuality', 'secret-token')
    settings = backup._payload('share')['sections']['settings']
    assert 'autoNextEpisodeEnabled' not in settings
    assert 'preferedQuality' not in settings


def test_share_profile_preserves_hoster_order_and_menu():
    set_setting('preferredHosters', '{"*": ["VOE", "Streamtape"]}')
    set_setting('mainMenuOrder', 'epicFavorites,settings,globalSearch')
    settings = backup._payload('share')['sections']['settings']
    assert json.loads(settings['preferredHosters']) == {'*': ['VOE', 'Streamtape']}
    assert settings['mainMenuOrder'] == 'epicFavorites,settings,globalSearch'


def test_addon_package_has_manifest_but_no_profile_or_cache(monkeypatch, tmp_path):
    (tmp_path / 'addon.xml').write_text('<addon id="plugin.video.gerxstream"/>')
    (tmp_path / 'resources').mkdir()
    (tmp_path / 'resources' / 'settings.xml').write_text('<settings/>')
    (tmp_path / 'resources' / 'cache').mkdir()
    (tmp_path / 'resources' / 'cache' / 'secret.json').write_text('secret')
    (tmp_path / 'userdata').mkdir()
    (tmp_path / 'userdata' / 'settings.xml').write_text('password')
    monkeypatch.setattr(cConfig, 'getAddonInfo', lambda self, key: str(tmp_path))
    target = io.BytesIO()
    backup._packageAddon(target)
    with zipfile.ZipFile(target) as package:
        assert package.namelist() == ['plugin.video.gerxstream/addon.xml',
                                     'plugin.video.gerxstream/resources/settings.xml']
        assert package.testzip() is None


def test_device_snapshot_roundtrip_includes_history_and_watched(monkeypatch, tmp_path):
    addonInfo = cConfig().getAddonInfo
    monkeypatch.setattr(cConfig, 'getAddonInfo', lambda self, key:
                        str(tmp_path) if key == 'profile' else addonInfo(key))
    monkeypatch.setattr(backup, '_settingIds', lambda: ({'autoNextEpisodeEnabled'}, {'account.pass'}))
    monkeypatch.setattr(backup.epicfavorites, 'exportData',
                        lambda: {'version': 2, 'folders': [], 'entries': [], 'watchlist': []})
    monkeypatch.setattr(backup.epicfavorites, 'importData', lambda data: True)
    watched = {'a' * 64: 123}
    history = [{'title': 'Episode', 'watched_at': 123}]
    assert backup._saveLocalData('watched', watched)
    assert backup._saveLocalData('history', history)
    payload = backup._payload('portable')
    assert 'accounts' not in payload['sections']
    assert payload['sections']['watched'] == watched
    assert payload['sections']['history'] == history
    assert backup._saveLocalData('watched', {})
    assert backup._importSections(payload, backup._requestedSections('portable'))
    assert backup._localData('watched') == watched


def test_legacy_complete_backup_remains_importable():
    payload = {'sections': {'settings': {}, 'accounts': {}, 'epic_favorites': {}}}
    assert backup._requestedSections('all', payload) == ['settings', 'accounts', 'epic_favorites']


def test_invalid_watched_data_changes_nothing(monkeypatch):
    set_setting('autoNextEpisodeEnabled', 'false')
    payload = {'sections': {'settings': {'autoNextEpisodeEnabled': 'true'},
                            'watched': {'invalid-key': 123}}}
    assert not backup._importSections(payload, ['settings', 'watched'])
    assert cConfig().getSettingString('autoNextEpisodeEnabled') == 'false'


def test_invalid_favorites_are_rejected_before_settings_change(monkeypatch):
    set_setting('autoNextEpisodeEnabled', 'false')
    monkeypatch.setattr(backup.epicfavorites, 'importData', lambda data: False)
    payload = {'sections': {'settings': {'autoNextEpisodeEnabled': 'true'},
                            'epic_favorites': {'entries': 'invalid'}}}
    assert backup._importSections(payload, ['settings', 'epic_favorites']) is False
    assert cConfig().getSettingString('autoNextEpisodeEnabled') == 'false'


def test_vfs_failed_write_is_not_reported_as_success(monkeypatch):
    class Destination:
        def __init__(self, *args):
            pass

        def write(self, content):
            return False

        def close(self):
            pass

    monkeypatch.setattr(backup, 'VfsFile', Destination)
    assert backup._writePayload('smb://server/backup.json', {}) is False


@pytest.mark.parametrize('endpoint', [
    'http://cloud.test/remote.php/dav/files/user/',
    'https://user:password@cloud.test/files/',
    'https://cloud.test/files/?token=secret',
    'https://cloud.test/files/../other/',
    'https://cloud.test/files/%2e%2e/other/',
])
def test_cloud_rejects_unsafe_endpoints(endpoint):
    set_setting('backupCloudUrl', endpoint)
    with pytest.raises(backup.BackupTransferError):
        backup._cloudUrl()


def test_remote_paths_use_forward_slashes():
    assert backup._joinPath('smb://server/backups', 'backup.json') == 'smb://server/backups/backup.json'


def test_cloud_listing_ignores_other_hosts_and_traversal(monkeypatch):
    set_setting('backupCloudUrl', 'https://cloud.test/files/user')
    filename = 'gerxstream-portable-20261009-120000-abcdef12.json'
    listing = '<d:multistatus xmlns:d="DAV:">%s</d:multistatus>' % ''.join(
        '<d:response><d:href>%s</d:href></d:response>' % href for href in (
            '/files/user/' + filename,
            'https://attacker.test/files/user/' + filename,
            '/files/user/../other/' + filename,
            '/files/user/%2e%2e/' + filename,
            '/files/user/not-a-backup.json',
        ))
    monkeypatch.setattr(backup, '_cloudRequest', lambda *args: listing.encode())
    assert backup._cloudFiles() == [filename]


@pytest.mark.parametrize('status', [302, 401, 412, 500])
def test_cloud_never_accepts_redirects_or_failed_uploads(monkeypatch, status):
    import requests
    set_setting('backupCloudUrl', 'https://cloud.test/files/user')
    set_setting('backupCloudUser', 'user')
    set_setting('backupCloudPassword', 'app-password')
    calls = []

    class Response:
        status_code = status

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Session(Response):
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            return Response()

    monkeypatch.setattr(requests, 'Session', Session)
    with pytest.raises(backup.BackupTransferError):
        backup._cloudRequest('PUT', 'gerxstream-share-20261009-120000.json', b'{}')
    assert calls[0][2]['allow_redirects'] is False
    assert calls[0][2]['verify'] is True
    assert calls[0][2]['headers']['If-None-Match'] == '*'


def test_selected_cloud_backup_can_include_accounts(monkeypatch):
    set_setting('autoNextEpisodeEnabled', 'true')
    set_setting('source.password', 'example-password')
    monkeypatch.setattr(backup, '_settingIds', lambda: ({'autoNextEpisodeEnabled'}, {'source.password'}))
    uploaded = []
    warnings = []
    selections = []

    class Dialog:
        def multiselect(self, title, options, **kwargs):
            selections.append(kwargs['preselect'])
            return [0, 1]

        def yesno(self, *args):
            warnings.append(args)
            return True

        def ok(self, *args):
            return True

    monkeypatch.setattr(backup.xbmcgui, 'Dialog', Dialog)
    monkeypatch.setattr(backup, '_storage', lambda dialog: 'nextcloud')
    monkeypatch.setattr(backup, '_cloudRequest', lambda *args: uploaded.append(args))
    assert backup.exportBackup('custom')
    assert 1 not in selections[0]
    assert len(warnings) == 1
    assert uploaded[0][0] == 'PUT'
    payload = backup._decodePayload(uploaded[0][2])
    assert set(payload['sections']) == {'settings', 'accounts'}
    assert payload['sections']['accounts']['source.password'] == 'example-password'


def test_account_warning_cancellation_prevents_cloud_upload(monkeypatch):
    class Dialog:
        def multiselect(self, *args, **kwargs):
            return [1]

        def yesno(self, *args):
            return False

    monkeypatch.setattr(backup.xbmcgui, 'Dialog', Dialog)
    monkeypatch.setattr(backup, '_cloudRequest', lambda *args: pytest.fail('Cancelled backup uploaded'))
    assert backup.exportBackup('custom') is False


def test_selected_import_leaves_unselected_accounts_unchanged(monkeypatch):
    set_setting('autoNextEpisodeEnabled', 'false')
    set_setting('source.password', 'device-password')
    monkeypatch.setattr(backup, '_settingIds', lambda: ({'autoNextEpisodeEnabled'}, {'source.password'}))
    payload = {'sections': {'settings': {'autoNextEpisodeEnabled': 'true'},
                            'accounts': {'source.password': 'cloud-password'}}}
    assert backup._importSections(payload, ['settings'])
    assert cConfig().getSettingString('autoNextEpisodeEnabled') == 'true'
    assert cConfig().getSettingString('source.password') == 'device-password'


def test_selected_cloud_import_applies_accounts_when_requested(monkeypatch, real_strings):
    set_setting('autoNextEpisodeEnabled', 'false')
    set_setting('source.password', 'device-password')
    monkeypatch.setattr(backup, '_settingIds', lambda: ({'autoNextEpisodeEnabled'}, {'source.password'}))
    payload = {'format': backup.FORMAT, 'format_version': backup.FORMAT_VERSION,
               'profile': 'custom',
               'sections': {'settings': {'autoNextEpisodeEnabled': 'true'},
                            'accounts': {'source.password': 'cloud-password'}}}
    confirmations = []

    class Dialog:
        def select(self, *args):
            return 0

        def multiselect(self, *args, **kwargs):
            return [0, 1]

        def yesno(self, *args):
            confirmations.append(args)
            return True

        def ok(self, *args):
            return True

    monkeypatch.setattr(backup.xbmcgui, 'Dialog', Dialog)
    monkeypatch.setattr(backup, '_storage', lambda dialog: 'nextcloud')
    monkeypatch.setattr(backup, '_cloudFiles', lambda: ['gerxstream-custom-20261009-120000.json'])
    monkeypatch.setattr(backup, '_cloudRequest', lambda *args: json.dumps(payload).encode('utf-8'))
    assert backup.importBackup('custom')
    assert len(confirmations) == 1
    assert 'Konten' in confirmations[0][1]
    assert cConfig().getSettingString('autoNextEpisodeEnabled') == 'true'
    assert cConfig().getSettingString('source.password') == 'cloud-password'


@pytest.mark.parametrize('password', ['app-password', ''])
def test_webdav_can_be_configured_directly_and_cancel_preserves_settings(monkeypatch, password):
    set_setting('backupStorage', 'folder')
    responses = iter(['https://cloud.test/remote.php/dav/files/user/backups', 'user', password])
    inputs = []

    class Dialog:
        def select(self, *args):
            return 1

        def yesno(self, *args):
            return True

        def input(self, *args, **kwargs):
            inputs.append(kwargs)
            return next(responses)

    monkeypatch.setattr(backup.xbmcgui, 'Dialog', Dialog)
    monkeypatch.setattr(backup.xbmcgui, 'ALPHANUM_HIDE_INPUT', 1, raising=False)
    assert backup.configureStorage() is bool(password)
    assert inputs[-1]['option'] == 1
    if password:
        assert cConfig().getSettingString('backupStorage') == 'nextcloud'
        assert cConfig().getSettingString('backupCloudUser') == 'user'
        assert cConfig().getSettingString('backupCloudPassword') == password
    else:
        assert cConfig().getSettingString('backupStorage') == 'folder'
        assert cConfig().getSettingString('backupCloudUser') == ''


def test_webdav_setup_rejects_http_before_requesting_credentials(monkeypatch):
    inputs = []

    class Dialog:
        def select(self, *args):
            return 1

        def yesno(self, *args):
            return True

        def input(self, *args, **kwargs):
            inputs.append(args)
            return 'http://cloud.test/files/user'

        def ok(self, *args):
            return True

    monkeypatch.setattr(backup.xbmcgui, 'Dialog', Dialog)
    assert not backup.configureStorage()
    assert len(inputs) == 1
    assert cConfig().getSettingString('backupCloudUser') == ''