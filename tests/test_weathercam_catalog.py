# -*- coding: utf-8 -*-
"""The stand-alone webcam source supports nested categories and JPEG cameras."""

from sites import weathercams


def test_nested_category_includes_its_descendant_cameras(monkeypatch):
    catalog = {
        'categories': [
            {'id': 'mountains'},
            {'id': 'mountains-de', 'parent': 'mountains'},
        ],
        'cameras': [
            {'id': 'summit', 'title': 'Summit', 'category': 'mountains-de',
             'stream': 'https://example.test/current.jpg',
             'source_url': 'https://example.test/source', 'protocol': 'jpeg'},
        ],
    }
    monkeypatch.setattr(weathercams, '_catalog', lambda: catalog)

    assert weathercams._categoryAndDescendants('mountains') == {'mountains', 'mountains-de'}
    assert [camera['id'] for camera in weathercams._camerasForCategory('mountains')] == ['summit']
