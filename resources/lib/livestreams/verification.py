# -*- coding: utf-8 -*-
# Python 3
"""SourceVerification: maschinenlesbare Mindestvalidierung des Katalogs.

Prueft rohe Kanaldaten gegen das Schema, findet doppelte Kanal-IDs und
doppelte Quellen-URLs, zaehlt inaktive Varianten und weist aus, welche Kanaele
mangels belegter Rechtelage aus dem Standardkatalog fallen (fail-closed).

Reines Datenmodul ohne Netz/Kodi-UI - direkt test- und skriptbar. Eine duenne
Kodi-Aktion (`report_dialog`) fasst das Ergebnis fuer den Nutzer zusammen.
"""

from resources.lib.livestreams import model

REQUIRED_CHANNEL_FIELDS = ('name', 'section')


def verify_channels(raw_channels):
    """Rohe Kanalliste pruefen. Gibt einen maschinenlesbaren Bericht zurueck."""
    report = {
        'total': 0,
        'valid': 0,
        'invalid': [],            # [{'index', 'name', 'reason'}]
        'duplicate_ids': [],      # [id, ...]
        'duplicate_source_urls': [],
        'inactive_sources': 0,
        'unknown_rights_channels': [],  # gueltig, aber keine freigegebene Quelle
        'approved_channels': 0,
    }
    seen_ids = {}
    seen_urls = {}

    for index, raw in enumerate(raw_channels or []):
        report['total'] += 1
        # Schema-Grobpruefung vor der Normalisierung fuer klare Fehlermeldungen.
        if not isinstance(raw, dict):
            report['invalid'].append({'index': index, 'name': '', 'reason': 'kein Objekt'})
            continue
        missing = [f for f in REQUIRED_CHANNEL_FIELDS if not raw.get(f)]
        if missing:
            report['invalid'].append({'index': index, 'name': raw.get('name', ''),
                                      'reason': 'Pflichtfelder fehlen: %s' % ','.join(missing)})
            continue

        channel = model.normalize_channel(raw)
        if channel is None:
            report['invalid'].append({'index': index, 'name': raw.get('name', ''),
                                      'reason': 'ungueltig (Sektion/Quelle/nsfw)'})
            continue

        report['valid'] += 1

        # Duplikat-IDs.
        cid = channel['id']
        if cid in seen_ids:
            report['duplicate_ids'].append(cid)
        seen_ids[cid] = True

        approved = 0
        for source in channel['sources']:
            if not source.get('active', True):
                report['inactive_sources'] += 1
            url = source['url']
            if url in seen_urls:
                report['duplicate_source_urls'].append(url)
            seen_urls[url] = True
            if source.get('active', True) and source.get('rights_status') == model.RIGHTS_APPROVED:
                approved += 1

        if approved > 0:
            report['approved_channels'] += 1
        else:
            report['unknown_rights_channels'].append(cid)

    report['ok'] = (not report['invalid']
                    and not report['duplicate_ids']
                    and report['approved_channels'] > 0)
    return report


def verify_registered():
    """Alle registrierten Provider einsammeln und pruefen."""
    from resources.lib.livestreams.providers import base as providers
    raw = []
    for provider in providers.registered_providers():
        try:
            raw.extend(provider.channels() or [])
        except Exception:
            continue
    return verify_channels(raw)


def summarize(report):
    return (
        'Kanaele gesamt: %(total)d\n'
        'gueltig: %(valid)d, freigegeben: %(approved_channels)d\n'
        'ungueltig: %(n_invalid)d, doppelte IDs: %(n_dup)d\n'
        'ohne Rechtebeleg (ausgeschlossen): %(n_unknown)d\n'
        'inaktive Varianten: %(inactive_sources)d'
    ) % {
        'total': report['total'], 'valid': report['valid'],
        'approved_channels': report['approved_channels'],
        'n_invalid': len(report['invalid']), 'n_dup': len(report['duplicate_ids']),
        'n_unknown': len(report['unknown_rights_channels']),
        'inactive_sources': report['inactive_sources'],
    }


def report_dialog():
    """Kodi-Aktion: Katalog pruefen und Ergebnis anzeigen (fail-soft)."""
    try:
        import xbmcgui
        report = verify_registered()
        xbmcgui.Dialog().textviewer('GerXStream - Quellenpruefung', summarize(report))
    except Exception:
        pass
