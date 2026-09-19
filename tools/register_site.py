# -*- coding: utf-8 -*-
# Python 3
"""Traegt ein neues Site-Plugin an allen Registrierungsstellen ein.

Ein Site-Plugin ist nicht nutzbar, solange es nicht in resources/settings.xml
und in beiden strings.po steht. Von Hand sind das pro Quelle rund 40 Zeilen an
drei Stellen - fehleranfaellig und schlecht nachvollziehbar. Dieses Skript
macht es reproduzierbar und ist idempotent: eine bereits eingetragene Quelle
wird nicht doppelt angelegt.

    python tools/register_site.py <id> <labelId> <Anzeigename> [--vod]

Beispiel:

    python tools/register_site.py mediaccc 30794 "media.ccc.de"
"""

import argparse
import io
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(PROJECT_ROOT, 'resources', 'settings.xml')
POFILES = {
    'de_de': os.path.join(PROJECT_ROOT, 'resources', 'language',
                          'resource.language.de_de', 'strings.po'),
    'en_gb': os.path.join(PROJECT_ROOT, 'resources', 'language',
                          'resource.language.en_gb', 'strings.po'),
}

# Ende der Kategorie, in die neue Quellen einsortiert werden.
CATEGORY_END = {
    False: '\t\t</category>\n\t\t<category id="indexsiteVoD"',
    True: '\t\t</category>\n\t\t<category id="tmdb"',
}

GROUP_TEMPLATE = """\t\t\t<group id="{sid}" label="{label}">
\t\t\t\t<setting id="plugin_{sid}" type="boolean" label="30050" help="30411">
\t\t\t\t\t<level>0</level>
\t\t\t\t\t<default>False</default>
\t\t\t\t\t<control type="toggle"/>
\t\t\t\t</setting>
\t\t\t\t<setting id="plugin_{sid}_allowInsecureTLS" type="boolean" label="30813" help="30814">
\t\t\t\t\t<level>3</level>
\t\t\t\t\t<default>False</default>
\t\t\t\t\t<dependencies>
\t\t\t\t\t\t<dependency type="enable" operator="!is" setting="plugin_{sid}">false</dependency>
\t\t\t\t\t\t<dependency type="visible" operator="!is" setting="plugin_{sid}">false</dependency>
\t\t\t\t\t</dependencies>
\t\t\t\t\t<control type="toggle"/>
\t\t\t\t</setting>
\t\t\t\t<setting id="global_search_{sid}" type="boolean" label="30052">
\t\t\t\t\t<level>0</level>
\t\t\t\t\t<default>False</default>
\t\t\t\t\t<dependencies>
\t\t\t\t\t\t<dependency type="enable" operator="!is" setting="plugin_{sid}">False</dependency>
\t\t\t\t\t</dependencies>
\t\t\t\t\t<control type="toggle"/>
\t\t\t\t</setting>
\t\t\t\t<setting id="plugin_{sid}_checkDomain" type="boolean" label="30051">
\t\t\t\t\t<level>3</level>
\t\t\t\t\t<default>False</default>
\t\t\t\t\t<dependencies>
\t\t\t\t\t\t<dependency type="enable" operator="!is" setting="plugin_{sid}">False</dependency>
\t\t\t\t\t</dependencies>
\t\t\t\t\t<control type="toggle"/>
\t\t\t\t</setting>
\t\t\t\t<setting id="plugin_{sid}_status" type="string" label="Dummy" help="">
\t\t\t\t\t<visible>false</visible>
\t\t\t\t\t<default>true</default>
\t\t\t\t\t<control type="toggle"/>
\t\t\t\t</setting>
\t\t\t\t<setting id="plugin_{sid}_bypassCookie" type="string" label="30826" help="30828">
\t\t\t\t\t<level>3</level>
\t\t\t\t\t<default/>
\t\t\t\t\t<constraints>
\t\t\t\t\t\t<allowempty>true</allowempty>
\t\t\t\t\t</constraints>
\t\t\t\t\t<dependencies>
\t\t\t\t\t\t<dependency type="enable" operator="!is" setting="plugin_{sid}">false</dependency>
\t\t\t\t\t\t<dependency type="visible" operator="!is" setting="plugin_{sid}">false</dependency>
\t\t\t\t\t</dependencies>
\t\t\t\t\t<control type="edit" format="string">
\t\t\t\t\t\t<heading>30826</heading>
\t\t\t\t\t</control>
\t\t\t\t</setting>
\t\t\t\t<setting id="plugin_{sid}_bypassUserAgent" type="string" label="30827" help="30828">
\t\t\t\t\t<level>3</level>
\t\t\t\t\t<default/>
\t\t\t\t\t<constraints>
\t\t\t\t\t\t<allowempty>true</allowempty>
\t\t\t\t\t</constraints>
\t\t\t\t\t<dependencies>
\t\t\t\t\t\t<dependency type="enable" operator="!is" setting="plugin_{sid}">false</dependency>
\t\t\t\t\t\t<dependency type="visible" operator="!is" setting="plugin_{sid}">false</dependency>
\t\t\t\t\t</dependencies>
\t\t\t\t\t<control type="edit" format="string">
\t\t\t\t\t\t<heading>30827</heading>
\t\t\t\t\t</control>
\t\t\t\t</setting>
\t\t\t\t<setting id="plugin_{sid}.domain" type="string" label="30278" help="">
\t\t\t\t\t<level>3</level>
\t\t\t\t\t<default/>
\t\t\t\t\t<constraints>
\t\t\t\t\t\t<allowempty>true</allowempty>
\t\t\t\t\t</constraints>
\t\t\t\t\t<dependencies>
\t\t\t\t\t\t<dependency type="enable" operator="!is" setting="plugin_{sid}">false</dependency>
\t\t\t\t\t\t<dependency type="visible" operator="!is" setting="plugin_{sid}">false</dependency>
\t\t\t\t\t</dependencies>
\t\t\t\t\t<control type="edit" format="string">
\t\t\t\t\t\t<heading>30278</heading>
\t\t\t\t\t</control>
\t\t\t\t</setting>
\t\t\t</group>
"""


def labelAlreadyTaken(label):
    """True wenn die String-ID bereits fuer einen ANDEREN Text vergeben
    ist. Ohne diese Pruefung kann ein bereits genutztes Label versehentlich
    einer neuen Quelle zugewiesen werden - die Einstellungsgruppe zeigt dann
    den falschen Namen an, und addPoEntry() legt keinen neuen Eintrag an,
    weil die ID schon existiert. Genau das ist einmal passiert (KayoAnime
    erhielt label=30800, das bereits 'Action' bedeutete)."""
    for path in POFILES.values():
        with io.open(path, encoding='utf-8') as fh:
            if 'msgctxt "#%s"' % label in fh.read():
                return True
    return False


def addSettingsGroup(sid, label, isVod):
    with io.open(SETTINGS, encoding='utf-8') as fh:
        content = fh.read()
    if 'id="plugin_%s"' % sid in content:
        return False
    if labelAlreadyTaken(label):
        raise SystemExit(
            'String-ID #%s ist bereits vergeben - eine freie ID waehlen.'
            % label)
    anchor = CATEGORY_END[isVod]
    if anchor not in content:
        raise SystemExit('Einfuegemarke nicht gefunden: %r' % anchor)
    block = GROUP_TEMPLATE.format(sid=sid, label=label)
    content = content.replace(anchor, block + anchor, 1)
    with io.open(SETTINGS, 'w', encoding='utf-8', newline='') as fh:
        fh.write(content)
    return True


def addPoEntry(path, label, text, isSource):
    with io.open(path, encoding='utf-8') as fh:
        content = fh.read()
    if '#%s' % label in content:
        return False
    # Nach dem hoechsten vorhandenen msgctxt anhaengen, Reihenfolge egal.
    entry = '\nmsgctxt "#%s"\nmsgid "%s"\nmsgstr "%s"\n' % (
        label, text, '' if isSource else text)
    if not content.endswith('\n'):
        content += '\n'
    content += entry
    with io.open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(content)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description='Registriert ein Site-Plugin.')
    parser.add_argument('sid', help='SITE_IDENTIFIER, z. B. mediaccc')
    parser.add_argument('label', help='freie String-ID fuer das Gruppenlabel')
    parser.add_argument('name', help='Anzeigename, z. B. "media.ccc.de"')
    parser.add_argument('--vod', action='store_true',
                        help='in die VoD-Kategorie statt indexsite2')
    args = parser.parse_args(argv)

    if not re.fullmatch(r'[a-z0-9_-]+', args.sid):
        # Dieselbe Regel wie die TLS-Pruefung in requestHandler.
        raise SystemExit('Ungueltiger SITE_IDENTIFIER: %r' % args.sid)
    if not os.path.isfile(os.path.join(PROJECT_ROOT, 'sites', args.sid + '.py')):
        raise SystemExit('sites/%s.py existiert nicht' % args.sid)

    done = []
    if addSettingsGroup(args.sid, args.label, args.vod):
        done.append('settings.xml')
    for lang, path in POFILES.items():
        if addPoEntry(path, args.label, args.name, lang == 'en_gb'):
            done.append(lang)

    print('%s (#%s): %s' % (args.sid, args.label,
                            ', '.join(done) if done else 'bereits registriert'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
