# -*- coding: utf-8 -*-
"""visible_pool_ids: respektiert Sektion, NSFW und Rabbithole-Kategorien."""
from resources.lib.livestreams import model, catalog, rabbithole
from resources.lib.config import cConfig


def _mk(name, section, genres, nsfw=False):
    return model.normalize_channel({
        'name': name, 'section': section, 'country': 'us', 'nsfw': nsfw,
        'genre': genres, 'sources': [{'url': 'https://x/%s.m3u8' % name, 'official': True}]})


def _pool(monkeypatch, channels):
    monkeypatch.setattr(catalog, 'load_all', lambda force=False: channels)


def test_pool_respects_section_and_nsfw(monkeypatch):
    _pool(monkeypatch, [
        _mk('CamNature', 'webcam', ['nature']),
        _mk('CamNSFW', 'webcam', ['adult'], nsfw=True),
        _mk('TV', 'tv', ['news']),
    ])
    cConfig().setSetting('showAdult', 'false')
    cConfig().setSetting('rhCategories', '')
    ids = rabbithole.visible_pool_ids()
    assert any('camnature' in i for i in ids)
    assert not any('nsfw' in i for i in ids)      # NSFW aus -> raus
    assert not any(i.startswith('gxs:tv') for i in ids)  # falsche Sektion


def test_pool_respects_rabbithole_categories(monkeypatch):
    _pool(monkeypatch, [
        _mk('Mountains', 'webcam', ['mountains']),
        _mk('Birds', 'webcam', ['birds']),
    ])
    cConfig().setSetting('showAdult', 'false')
    cConfig().setSetting('rhCategories', 'mountains')
    ids = rabbithole.visible_pool_ids()
    assert any('mountains' in i for i in ids)
    assert not any('birds' in i for i in ids)
