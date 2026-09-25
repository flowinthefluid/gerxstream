# -*- coding: utf-8 -*-
"""Tests fuer die zentrale Sichtbarkeits-/NSFW-Logik (fail-closed)."""
import pytest

from resources.lib import contentgate
from resources.lib.config import cConfig


def _set(**kwargs):
    for key, value in kwargs.items():
        cConfig().setSetting(key, value)


# --- NSFW-Achse -----------------------------------------------------------

@pytest.mark.parametrize('raw, expected', [
    ('true', True), ('True', True), ('1', True), ('yes', True), ('on', True),
    ('false', False), ('', False), ('0', False), ('nonsense', False),
])
def test_nsfw_boolean_semantics(raw, expected):
    _set(showAdult=raw)
    assert contentgate.is_nsfw_enabled() is expected


def test_channel_hidden_when_nsfw_flag_missing():
    """Fail-closed: ein fehlendes nsfw-Feld wird wie NSFW behandelt.

    Sicherheitsrelevant ist der Zustand 'Schalter aus' - dann bleibt ein
    unmarkierter Kanal garantiert unsichtbar. Bei aktivem Schalter erscheint
    er (als NSFW eingestuft) zusammen mit den uebrigen Erwachsenen-Inhalten.
    """
    channel = {'name': 'X', 'section': 'tv', 'country': 'de', 'genre': []}  # kein nsfw
    _set(showAdult='false')
    assert contentgate.is_channel_visible(channel) is False
    _set(showAdult='true')
    assert contentgate.is_channel_visible(channel) is True


def test_channel_hidden_on_broken_record():
    _set(showAdult='true')
    assert contentgate.is_channel_visible(None) is False
    assert contentgate.is_channel_visible('not-a-dict') is False


def test_nsfw_channel_hidden_when_disabled():
    _set(showAdult='false')
    channel = {'name': 'Adult', 'section': 'tv', 'country': 'de',
               'genre': ['adult'], 'nsfw': True}
    assert contentgate.is_channel_visible(channel) is False


def test_nsfw_channel_visible_when_enabled():
    _set(showAdult='true')
    channel = {'name': 'Adult', 'section': 'tv', 'country': 'de',
               'genre': ['adult'], 'nsfw': True}
    assert contentgate.is_channel_visible(channel) is True


def test_genre_selection_never_enables_nsfw():
    """Auch wenn 'adult' als sichtbares Genre gilt, bleibt NSFW ohne Schalter aus."""
    _set(showAdult='false', lsGenresHidden='')  # adult NICHT versteckt
    channel = {'name': 'Adult', 'section': 'tv', 'country': 'de',
               'genre': ['adult'], 'nsfw': True}
    assert contentgate.is_channel_visible(channel) is False


def test_mislabeled_nsfw_caught_by_heuristic():
    """nsfw:false, aber Name/Genre verraten Erotik -> bei Gate aus versteckt."""
    _set(showAdult='false')
    channel = {'name': 'Hardcore XXX', 'section': 'tv', 'country': 'de',
               'genre': ['movies'], 'nsfw': False}
    assert contentgate.is_channel_visible(channel) is False
    _set(showAdult='true')
    assert contentgate.is_channel_visible(channel) is True


# --- Bereiche / Laender / Genres -----------------------------------------

def test_section_visibility_default_true():
    channel = {'name': 'ARD', 'section': 'tv', 'country': 'de',
               'genre': ['news'], 'nsfw': False}
    assert contentgate.is_channel_visible(channel) is True


def test_section_can_be_hidden():
    _set(lsSectionTv='false')
    channel = {'name': 'ARD', 'section': 'tv', 'country': 'de',
               'genre': ['news'], 'nsfw': False}
    assert contentgate.is_channel_visible(channel) is False


def test_unknown_section_hidden():
    channel = {'name': 'X', 'section': 'bogus', 'country': 'de',
               'genre': ['news'], 'nsfw': False}
    assert contentgate.is_channel_visible(channel) is False


def test_country_whitelist():
    _set(lsCountryMode='whitelist', lsCountries='de,hr')
    visible = {'name': 'ARD', 'section': 'tv', 'country': 'de', 'genre': [], 'nsfw': False}
    hidden = {'name': 'BBC', 'section': 'tv', 'country': 'gb', 'genre': [], 'nsfw': False}
    assert contentgate.is_channel_visible(visible) is True
    assert contentgate.is_channel_visible(hidden) is False


def test_country_blacklist():
    _set(lsCountryMode='blacklist', lsCountries='us')
    de = {'name': 'ARD', 'section': 'tv', 'country': 'de', 'genre': [], 'nsfw': False}
    us = {'name': 'CNN', 'section': 'tv', 'country': 'us', 'genre': [], 'nsfw': False}
    assert contentgate.is_channel_visible(de) is True
    assert contentgate.is_channel_visible(us) is False


def test_get_visible_countries_preserves_order():
    _set(lsCountryMode='whitelist', lsCountries='hr,de')
    result = contentgate.get_visible_countries(['de', 'us', 'hr', 'gb'])
    assert result == ['de', 'hr']


def test_genre_hidden_removes_channel_when_all_hidden():
    _set(lsGenresHidden='news')
    only_news = {'name': 'N24', 'section': 'tv', 'country': 'de',
                 'genre': ['news'], 'nsfw': False}
    mixed = {'name': 'Mix', 'section': 'tv', 'country': 'de',
             'genre': ['news', 'music'], 'nsfw': False}
    assert contentgate.is_channel_visible(only_news) is False
    assert contentgate.is_channel_visible(mixed) is True


def test_filter_channels_generator():
    _set(showAdult='false')
    channels = [
        {'name': 'ARD', 'section': 'tv', 'country': 'de', 'genre': ['news'], 'nsfw': False},
        {'name': 'XXX', 'section': 'tv', 'country': 'de', 'genre': ['adult'], 'nsfw': True},
    ]
    result = list(contentgate.filter_channels(channels))
    assert [c['name'] for c in result] == ['ARD']


# --- Cache-Fingerprint ----------------------------------------------------

def test_fingerprint_changes_with_nsfw():
    _set(showAdult='false')
    before = contentgate.visibility_fingerprint()
    _set(showAdult='true')
    after = contentgate.visibility_fingerprint()
    assert before != after


def test_fingerprint_changes_with_country_and_genre():
    base = contentgate.visibility_fingerprint()
    _set(lsCountryMode='whitelist', lsCountries='de')
    assert contentgate.visibility_fingerprint() != base
    mid = contentgate.visibility_fingerprint()
    _set(lsGenresHidden='news')
    assert contentgate.visibility_fingerprint() != mid


def test_fingerprint_stable_without_change():
    _set(showAdult='true', lsCountries='de,hr')
    assert contentgate.visibility_fingerprint() == contentgate.visibility_fingerprint()
