import pytest
import sys
from pathlib import Path
from xml.etree import ElementTree

from conftest import set_setting
from sites import rocketbeans


def test_rocketbeans_selects_only_matching_free_episode():
    result = {'data': {'episodes': [
        {'id': 1, 'isAvailable': True, 'tokens': [{'type': 'youtube', 'token': 'y3thJ4vHB5k'}]},
        {'id': 2, 'isAvailable': True, 'rbscExclusive': True,
         'tokens': [{'type': 'youtube', 'token': 'y3thJ4vHB5k'}]}]}}
    assert rocketbeans._youtubeId(result, '1') == 'y3thJ4vHB5k'
    assert rocketbeans._youtubeId(result, '2') == ''
    assert rocketbeans._youtubeId(result, '3') == ''


def test_rocketbeans_rejects_invalid_player_urls():
    assert rocketbeans.getHosterUrl('https://example.org/stream.m3u8') == []
    assert rocketbeans.getHosterUrl('plugin://plugin.video.youtube/play/?video_id=bad') == []
    assert rocketbeans.getHosterUrl('plugin://plugin.video.youtube/play/?video_id=y3thJ4vHB5k')[0]['resolved']


def test_rocketbeans_auth_uses_verified_tls_and_no_redirect(monkeypatch):
    calls = []
    set_setting(rocketbeans.TOKEN_SETTING, 'session-value')

    class Response:
        status_code = 200

        def json(self):
            return {'success': True, 'data': []}

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return Response()

    monkeypatch.setattr(rocketbeans.requests, 'request', request)
    rocketbeans._call('/v1/media/abobox/self')
    assert calls[0][1] == 'https://api.rocketbeans.tv/v1/media/abobox/self'
    assert calls[0][2]['headers']['Authorization'] == 'Bearer session-value'
    assert calls[0][2]['allow_redirects'] is False
    assert calls[0][2].get('verify', True) is True


def test_rocketbeans_expired_session_is_cleared(monkeypatch):
    from resources.lib.config import cConfig
    set_setting(rocketbeans.TOKEN_SETTING, 'expired')

    class Response:
        status_code = 401

    monkeypatch.setattr(rocketbeans.requests, 'request', lambda *args, **kwargs: Response())
    assert rocketbeans._call('/v1/media/abobox/self') == {}
    assert cConfig().getSetting(rocketbeans.TOKEN_SETTING) == ''


def test_rocketbeans_login_clears_password_and_does_not_send_old_token(monkeypatch):
    from resources.lib.config import cConfig
    calls = []
    set_setting('rocketbeans.user', 'test@example.test')
    set_setting('rocketbeans.pass', 'dummy-password')
    set_setting(rocketbeans.TOKEN_SETTING, 'old-session')

    class Dialog:
        def input(self, *args):
            return '123456'

    class Gui:
        def showInfo(self, *args):
            pass

    def call(path, **kwargs):
        calls.append((path, kwargs))
        return {'success': True, 'data': {'token': 'new-session'}}

    monkeypatch.setattr(rocketbeans.xbmcgui, 'Dialog', Dialog)
    monkeypatch.setattr(rocketbeans, 'cGui', Gui)
    monkeypatch.setattr(rocketbeans, '_call', call)
    assert rocketbeans.login()
    assert calls[0][0] == '/v1/auth/local'
    assert calls[0][1]['authenticated'] is False
    assert calls[0][1]['payload']['secondFactorToken'] == '123456'
    assert cConfig().getSetting('rocketbeans.pass') == ''
    assert cConfig().getSetting(rocketbeans.TOKEN_SETTING) == 'new-session'


@pytest.mark.parametrize('offset,expected', [('0', 0), ('50', 50), ('-1', 0), ('bad', 0)])
def test_rocketbeans_offsets_are_validated(offset, expected):
    class Params:
        def getValue(self, key):
            return offset

    assert rocketbeans._offset(Params()) == expected


@pytest.fixture
def navigation(monkeypatch):
    entries = []

    class Gui:
        def addFolder(self, element, params, folder=True, total=0):
            entries.append((element.getTitle(), element.getFunction(),
                            dict(params.getAllParameters()), folder))

        def addNextPage(self, site, function, params):
            entries.append(('next', function, dict(params.getAllParameters()), True))

        def setEndOfDirectory(self):
            pass

        def setView(self, *args):
            pass

    monkeypatch.setattr(rocketbeans, 'cGui', Gui)
    return entries


def test_rocketbeans_seasons_use_actual_api_names(monkeypatch, navigation):
    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?showId=136&offset=50'])
    monkeypatch.setattr(rocketbeans, '_call', lambda *args: {'data': {
        'seasons': [{'id': 42, 'name': '1648: Von Krieg und Frieden', 'thumbnail': []}]}})
    rocketbeans.showSeasons()
    assert navigation[0][2]['rbMode'] == 'show'
    assert navigation[1][0] == '1648: Von Krieg und Frieden'
    assert navigation[1][2]['seasonId'] == '42'
    assert navigation[1][2]['rbMode'] == 'season'
    assert navigation[1][2]['offset'] == '0'


def test_rocketbeans_episode_pagination_retains_season(monkeypatch, navigation):
    paths = []
    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?rbMode=season&seasonId=42&offset=50'])

    def call(path):
        paths.append(path)
        return {'data': [{'id': 123, 'title': 'Folge'}], 'pagination': {'total': 101}}

    monkeypatch.setattr(rocketbeans, '_call', call)
    rocketbeans.showEpisodes()
    assert paths == ['/v1/media/episode/byseason/preview/42?offset=50&limit=50&order=DESC']
    assert navigation[0][3] is False
    assert navigation[-1][0] == 'next'
    assert navigation[-1][2]['offset'] == '100'
    assert navigation[-1][2]['seasonId'] == '42'
    assert navigation[-1][2]['rbMode'] == 'season'


def test_rocketbeans_account_settings_use_real_routes():
    settings = ElementTree.parse(Path(__file__).resolve().parents[1] / 'resources' / 'settings.xml')
    account = settings.find(".//category[@id='account']/group[@id='rocketbeansacc']")
    assert account is not None
    for action in ('login', 'logout'):
        setting = account.find("setting[@id='rocketbeans.%s']" % action)
        assert setting.findtext('data') == ('RunPlugin(plugin://plugin.video.gerxstream/'
                                          '?site=rocketbeans&function=%s)' % action)
    assert account.find("setting[@id='rocketbeans.pass']/control/hidden").text == 'true'
    assert account.find("setting[@id='rocketbeans.token']/visible").text == 'false'


def test_rocketbeans_logout_clears_local_credentials_even_on_server_failure(monkeypatch):
    from resources.lib.config import cConfig
    set_setting(rocketbeans.TOKEN_SETTING, 'old-session')
    set_setting('rocketbeans.pass', 'dummy-password')
    monkeypatch.setattr(rocketbeans, '_call', lambda *args, **kwargs: {})
    monkeypatch.setattr(rocketbeans, 'cGui', lambda: type('Gui', (), {'showInfo': lambda *args: None})())
    rocketbeans.logout()
    assert cConfig().getSetting(rocketbeans.TOKEN_SETTING) == ''
    assert cConfig().getSetting('rocketbeans.pass') == ''