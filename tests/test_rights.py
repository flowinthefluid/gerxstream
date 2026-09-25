# -*- coding: utf-8 -*-
"""Rechte-Gate: ohne Freigabe-Beleg bleibt eine Quelle 'unknown' und der
Kanal aus dem Standardkatalog (fail-closed)."""
import pytest

from resources.lib.livestreams import model, catalog


@pytest.mark.parametrize('official, evidence, drm, login, expected', [
    (True,  '',                False, False, model.RIGHTS_APPROVED),   # offiziell
    (False, 'https://x/lic',   False, False, model.RIGHTS_APPROVED),   # Beleg vorhanden
    (False, '',                False, False, model.RIGHTS_UNKNOWN),    # nichts -> unknown
    (True,  '',                True,  False, model.RIGHTS_UNKNOWN),    # DRM -> unknown
    (True,  '',                False, True,  model.RIGHTS_UNKNOWN),    # Login -> unknown
])
def test_rights_status(official, evidence, drm, login, expected):
    src = model.normalize_source({
        'url': 'https://x/master.m3u8', 'official': official,
        'rights_evidence_url': evidence, 'drm': drm, 'login_required': login,
    })
    assert src['rights_status'] == expected


def test_unknown_source_excluded_from_catalog(monkeypatch):
    ch_approved = model.normalize_channel({
        'name': 'OK', 'section': 'webcam', 'country': 'us', 'nsfw': False,
        'sources': [{'url': 'https://x/a.m3u8', 'official': True}]})
    ch_unknown = model.normalize_channel({
        'name': 'NoRights', 'section': 'webcam', 'country': 'xx', 'nsfw': False,
        'sources': [{'url': 'http://y/video.mjpg', 'official': False}]})
    monkeypatch.setattr(catalog, 'load_all', lambda force=False: [ch_approved, ch_unknown])
    from resources.lib.config import cConfig
    cConfig().setSetting('showAdult', 'false')
    visible = [c['name'] for c in catalog.visible_channels()]
    assert 'OK' in visible
    assert 'NoRights' not in visible


def test_inactive_variant_not_approved():
    ch = model.normalize_channel({
        'name': 'Off', 'section': 'webcam', 'country': 'us', 'nsfw': False,
        'sources': [{'url': 'https://x/a.m3u8', 'official': True, 'active': False}]})
    assert catalog.approved_sources(ch) == []
