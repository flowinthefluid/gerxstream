# -*- coding: utf-8 -*-
"""Resolver transport errors are handled as an unavailable hoster, not crashes."""

from resources.lib.gui import hoster


def test_unexpected_resolver_error_returns_false_without_traceback(monkeypatch):
    shown = []

    class Resolver:
        class resolver:
            class ResolverError(Exception):
                pass

        @staticmethod
        def resolve(_url):
            raise RuntimeError('upstream hoster returned 404')

    class Gui:
        def showError(self, *args):
            shown.append(args)

    monkeypatch.setitem(__import__('sys').modules, 'resolveurl', Resolver)
    monkeypatch.setattr(hoster, 'cGui', Gui)
    monkeypatch.setattr(hoster.cHosterGui, '__init__', lambda self: None)

    gui = hoster.cHosterGui()
    assert gui._getInfoAndResolve({'streamUrl': 'https://example.test/item',
                                   'resolved': False}) is False
    assert shown
