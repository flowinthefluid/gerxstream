# -*- coding: utf-8 -*-
"""Credentials must never be included in request-handler log URLs."""

from resources.lib.handler.requestHandler import cRequestHandler


def test_sensitive_query_values_are_redacted_from_log_url():
    url = ('https://alice:secret@example.test/login?email=person%40example.test'
           '&password=super-secret&api_key=api-secret&access_token=token-secret'
           '&page=2')

    safe = cRequestHandler._safeUrlForLog(url)

    for secret in ('alice', 'secret', 'person%40example.test', 'super-secret',
                   'api-secret', 'token-secret'):
        assert secret not in safe
    assert 'page=2' in safe
    assert 'password=%3Credacted%3E' in safe


def test_safe_request_uri_uses_the_same_redaction():
    handler = cRequestHandler.__new__(cRequestHandler)
    handler._sUrl = 'https://example.test/login'
    handler._aParameters = {'email': 'person@example.test', 'password': 'secret'}

    safe = handler._safeRequestUriForLog()

    assert 'person%40example.test' not in safe
    assert 'secret' not in safe
    assert 'email=%3Credacted%3E' in safe
