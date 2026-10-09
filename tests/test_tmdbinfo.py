import pytest

from resources.lib import tmdbinfo


@pytest.mark.parametrize('missing_fields', [False, True, None])
def test_actor_filmography_uses_valid_page_and_optional_person_fields(monkeypatch, missing_fields):
    properties = {'gerxstream_menu': 'Cast'}
    listed = []
    calls = []
    notifications = []

    class Item:
        def getProperty(self, name):
            return '2296' if name == 'id' else ''

    class Control:
        def getSelectedItem(self):
            return Item()

        def addItems(self, items):
            listed.extend(items)

        def reset(self):
            listed.clear()

    class Window:
        def __init__(self, *args, **kwargs):
            pass

        def getControl(self, controlId):
            return Control()

        def getProperty(self, name):
            return properties.get(name, '')

        def setProperty(self, name, value):
            if not isinstance(value, str):
                raise TypeError('Kodi properties must be strings')
            properties[name] = value

        def setFocusId(self, controlId):
            pass

        def doModal(self):
            self.none_poster = 'no_cover.png'
            self.onClick(50)

    class TMDB:
        def get_meta(self, *args, **kwargs):
            return {'tmdb_id': '123', 'title': 'Carrie'}

        def getUrl(self, url, page=1, term=''):
            calls.append((url, page, term))
            if page != 1:
                raise ValueError('Invalid TMDB page')
            if missing_fields is None:
                return False
            data = {'name': 'Matthew Lillard', 'movie_credits': {'cast': [
                {'title': 'Scream', 'poster_path': None}]}, 'tv_credits': {'cast': [
                    {'name': 'Carrie', 'poster_path': None}, {}]}}
            if not missing_fields:
                data.update({'birthday': '1970-01-24', 'deathday': None,
                             'place_of_birth': None, 'biography': None})
            return data

        def imageUrl(self, path):
            return ''

    monkeypatch.setattr(tmdbinfo.xbmcgui, 'WindowXMLDialog', Window, raising=False)
    monkeypatch.setattr(tmdbinfo.xbmcgui.Dialog, 'select', lambda *args: 0)
    monkeypatch.setattr(tmdbinfo.xbmcgui.Dialog, 'notification', lambda *args: notifications.append(args))
    monkeypatch.setattr(tmdbinfo, 'cTMDB', TMDB)
    tmdbinfo.WindowsBoxes('Carrie', 'Carrie', 'tvshow')
    assert calls == [('person/2296', 1, 'append_to_response=movie_credits,tv_credits')]
    if missing_fields is None:
        assert properties['gerxstream_menu'] == 'Cast'
        assert len(notifications) == 1
        return
    assert properties['gerxstream_menu'] == 'Person'
    assert properties['Person_name'] == 'Matthew Lillard'
    assert properties['Person_place_of_birth'] == ''
    assert properties['Person_biography'] == ''
    assert [item._label for item in listed] == ['Scream', 'Carrie']
    assert not notifications