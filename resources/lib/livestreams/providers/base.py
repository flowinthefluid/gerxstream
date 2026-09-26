# -*- coding: utf-8 -*-
# Python 3
"""Provider-Abstraktion und Registry fuer den Source-Layer.

Ein Provider liefert rohe Kanal-`dict`s (``channels()``); Validierung,
Normalisierung, Rechte-Gate, Dublettenzusammenfuehrung und Caching passieren
zentral in ``catalog``. So bleibt der Source-Layer wartbar: neue Quellen sind
ein zusaetzliches Provider-Modul plus eine Registrierung, kein Eingriff in die
Kernlogik.

``signature()`` gibt eine billige Kennung des aktuellen Datenstands zurueck
(z.B. Datei-Mtimes), damit ``catalog`` seinen Prozess-Cache invalidieren kann,
ohne alles neu zu laden. ``channels()`` darf beim Menueaufbau NICHT ins Netz -
Netzabrufe gehoeren in den Service.
"""


class Provider(object):
    id = 'base'

    def channels(self):
        """Liste roher Kanal-dicts (vor der Normalisierung). Nie None."""
        return []

    def signature(self):
        """Billige Kennung des Datenstands fuer die Cache-Invalidierung."""
        return self.id


_REGISTRY = []


def register(provider):
    if provider not in _REGISTRY:
        _REGISTRY.append(provider)
    return provider


def registered_providers():
    """Alle registrierten Provider. Beim ersten Aufruf Standard-Provider laden."""
    if not _REGISTRY:
        _load_defaults()
    return list(_REGISTRY)


def reset():
    """Nur fuer Tests: Registry leeren."""
    _REGISTRY.clear()


def _load_defaults():
    # Kuratierte JSON-Kataloge (mitgeliefert + Nutzerprofil) sind der
    # Standard-Provider. Weitere Provider (dokumentierte APIs/Feeds) koennen
    # hier importiert und registriert werden - siehe docs §10.
    from resources.lib.livestreams.providers.curated import CuratedProvider
    register(CuratedProvider())
    from resources.lib.livestreams.providers.pluto import PlutoProvider
    register(PlutoProvider())
