# -*- coding: utf-8 -*-
"""SourceVerification gegen eine gemischte Fixture."""
import json
import os

from resources.lib.livestreams import verification

_FIX = os.path.join(os.path.dirname(__file__), 'fixtures', 'catalog_mixed.json')


def _load():
    with open(_FIX, encoding='utf-8') as handle:
        return json.load(handle)['channels']


def test_report_structure_and_counts():
    report = verification.verify_channels(_load())
    # 5 Eintraege: 1 broken (bogus section), 4 valide.
    assert report['total'] == 5
    assert report['valid'] == 4
    # Broken landet in invalid.
    assert any(x['name'] == 'Broken' for x in report['invalid'])


def test_duplicate_id_detected():
    report = verification.verify_channels(_load())
    assert 'gxs:tv:de:approved' in report['duplicate_ids']


def test_unknown_rights_excluded_and_listed():
    report = verification.verify_channels(_load())
    assert 'gxs:webcam:xx:norights' in report['unknown_rights_channels']
    # Approved-Kanaele: Approved TV + Evidence Cam.
    assert report['approved_channels'] >= 2


def test_inactive_source_counted():
    report = verification.verify_channels(_load())
    assert report['inactive_sources'] >= 1


def test_summarize_is_string():
    report = verification.verify_channels(_load())
    assert isinstance(verification.summarize(report), str)


def test_empty_input():
    report = verification.verify_channels([])
    assert report['total'] == 0
    assert report['ok'] is False
