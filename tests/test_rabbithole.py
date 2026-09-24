# -*- coding: utf-8 -*-
"""Rabbithole/Zufall respektieren Gate und Rechte."""
from resources.lib.livestreams import model, catalog
from resources.lib.config import cConfig


def _mk(name, section, nsfw, official=True):
    return model.normalize_channel({
        'name': name, 'section': section, 'country': 'us', 'nsfw': nsfw,
        'sources': [{'url': 'https://x/%s.m3u8' % name, 'official': official}]})


def test_rabbithole_pool_excludes_nsfw_and_unknown(monkeypatch):
    pool = [
        _mk('CamA', 'webcam', False, official=True),
        _mk('CamNSFW', 'webcam', True, official=True),
        _mk('CamNoRights', 'webcam', False, official=False),  # unknown rights
        _mk('TVchan', 'tv', False, official=True),             # falsche Sektion
    ]
    monkeypatch.setattr(catalog, 'load_all', lambda force=False: pool)
    cConfig().setSetting('showAdult', 'false')
    names = [c['name'] for c in catalog.visible_channels()
             if c['section'] in ('webcam', 'weather')]
    assert names == ['CamA']  # nur sichtbar + freigegeben + richtige Sektion


def test_dedupe_by_publisher(monkeypatch):
    a = {'name': 'Cam', 'section': 'webcam', 'country': 'us', 'nsfw': False,
         'publisher': 'p1', 'sources': [{'url': 'https://x/1.m3u8', 'official': True}]}
    b = {'name': 'Cam', 'section': 'webcam', 'country': 'us', 'nsfw': False,
         'publisher': 'p1', 'sources': [{'url': 'https://x/2.m3u8', 'official': True}]}
    merged = catalog._merge([model.normalize_channel(a), model.normalize_channel(b)])
    assert len(merged) == 1
    assert len(merged[0]['sources']) == 2  # zwei Varianten, ein Kanal
