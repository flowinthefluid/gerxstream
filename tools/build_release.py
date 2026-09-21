# -*- coding: utf-8 -*-
# Python 3
"""Baut das installierbare Kodi-Zip fuer GerXStream (Befund N13).

Kodi erwartet im Archiv genau einen Wurzelordner, der so heisst wie die
Addon-ID. Alles, was nur zur Entwicklung gehoert (Bytecode, Dokumentation,
Design-Quellen, CI-Vorlagen), bleibt draussen.

Aufruf aus dem Projektverzeichnis:

    python tools/build_release.py

Optionen:
    --out-dir DIR   Zielverzeichnis (Vorgabe: dist)
    --list          Nur auflisten, was aufgenommen wuerde; nichts schreiben
"""

import argparse
import fnmatch
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Verzeichnisse, die nie ins Release gehoeren. Exakte Namen, auf jeder Ebene.
EXCLUDED_DIRS = {
    '.git',
    '.github',
    '.tmp',
    '__pycache__',
    'design',
    'dist',
    'docs',
    'tests',
    'tools',
    '.idea',
    '.vscode',
    # Zeiger-Addons fuer das eigene Hosting-Repo (docs/REPO-SPEC.md); die
    # gehoeren als eigenstaendige Addons niemals ins Plugin-Zip.
    'repository.gerxstream',
    'repository.resolveurl',
}

# Dateien, die nie ins Release gehoeren. fnmatch-Muster gegen den Dateinamen.
EXCLUDED_FILE_PATTERNS = (
    '*.py[cod]',
    '*.zip',
    '*.swp',
    '.DS_Store',
    'Thumbs.db',
    '.gitignore',
    '.gitattributes',
    'ScraperInfo.txt',
    '_m2_warnings*.txt',
)

# Ohne diese Dateien ist das Archiv fuer Kodi nicht brauchbar.
REQUIRED_MEMBERS = (
    'addon.xml',
    'default.py',
    'service.py',
    'resources/settings.xml',
)


def readAddonMetadata(root):
    """Liest Addon-ID und Version aus der addon.xml."""
    addonXml = os.path.join(root, 'addon.xml')
    if not os.path.isfile(addonXml):
        raise SystemExit('addon.xml nicht gefunden: %s' % addonXml)
    node = ET.parse(addonXml).getroot()
    addonId = node.get('id')
    version = node.get('version')
    if not addonId or not version:
        raise SystemExit('addon.xml: id oder version fehlt')
    return addonId, version


def isExcludedFile(name):
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_FILE_PATTERNS)


def isExcludedPath(relPath):
    parts = relPath.split('/')
    if any(part in EXCLUDED_DIRS for part in parts[:-1]):
        return True
    return isExcludedFile(parts[-1])


def trackedFiles(root):
    """Von Git verwaltete Pfade, oder None wenn das nicht ermittelbar ist.

    Der Arbeitsbaum ist als Quelle ungeeignet: lose Vorlagen- und Rohdateien,
    die absichtlich nicht eingecheckt sind, landen sonst im Release. Beim
    ersten Bauversuch waren das 4,2 MB Bildmaterial. Was Git nicht kennt,
    gehoert nicht ins Paket.
    """
    try:
        result = subprocess.run(['git', '-C', root, 'ls-files', '-z'],
                                capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    paths = [p for p in result.stdout.decode('utf-8').split('\0') if p]
    return paths or None


def walkFiles(root):
    """Rueckfallweg ohne Git: laeuft ueber den Arbeitsbaum."""
    collected = []
    for dirPath, dirNames, fileNames in os.walk(root):
        # In-place filtern, damit os.walk die Zweige gar nicht erst betritt.
        dirNames[:] = sorted(d for d in dirNames if d not in EXCLUDED_DIRS)
        for fileName in sorted(fileNames):
            absPath = os.path.join(dirPath, fileName)
            relPath = os.path.relpath(absPath, root).replace(os.sep, '/')
            collected.append(relPath)
    return collected


def collectFiles(root):
    """Liefert die aufzunehmenden Pfade, relativ zu root, mit / als Trenner."""
    paths = trackedFiles(root)
    fromGit = paths is not None
    if not fromGit:
        paths = walkFiles(root)
    collected = sorted(p for p in paths
                       if not isExcludedPath(p)
                       and os.path.isfile(os.path.join(root, p)))
    return collected, fromGit


def buildZip(root, outDir, addonId, version, members):
    os.makedirs(outDir, exist_ok=True)
    target = os.path.join(outDir, '%s-%s.zip' % (addonId, version))
    # Deterministisch: feste Sortierung, feste Kompression.
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for relPath in members:
            archive.write(os.path.join(root, relPath), '%s/%s' % (addonId, relPath))
    return target


def verifyZip(path, addonId, members):
    """Prueft das geschriebene Archiv, bevor es als fertig gemeldet wird."""
    with zipfile.ZipFile(path) as archive:
        broken = archive.testzip()
        if broken is not None:
            raise SystemExit('Beschaedigter Eintrag im Archiv: %s' % broken)
        names = archive.namelist()

    roots = {name.split('/')[0] for name in names}
    if roots != {addonId}:
        raise SystemExit('Archiv hat nicht genau einen Wurzelordner %s: %s'
                         % (addonId, sorted(roots)))

    for required in REQUIRED_MEMBERS:
        if '%s/%s' % (addonId, required) not in names:
            raise SystemExit('Pflichtdatei fehlt im Archiv: %s' % required)

    for name in names:
        tail = name.split('/', 1)[1]
        if any(part in EXCLUDED_DIRS for part in tail.split('/')[:-1]):
            raise SystemExit('Ausgeschlossenes Verzeichnis im Archiv: %s' % name)
        if isExcludedFile(tail.split('/')[-1]):
            raise SystemExit('Ausgeschlossene Datei im Archiv: %s' % name)

    if len(names) != len(members):
        raise SystemExit('Archiv enthaelt %s Eintraege, erwartet waren %s'
                         % (len(names), len(members)))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Baut das Kodi-Release-Zip.')
    parser.add_argument('--out-dir', default=os.path.join(PROJECT_ROOT, 'dist'),
                        help='Zielverzeichnis (Vorgabe: dist)')
    parser.add_argument('--list', action='store_true',
                        help='Nur auflisten, nichts schreiben')
    args = parser.parse_args(argv)

    addonId, version = readAddonMetadata(PROJECT_ROOT)
    members, fromGit = collectFiles(PROJECT_ROOT)
    quelle = 'git ls-files' if fromGit else 'Arbeitsbaum (kein Git)'

    if args.list:
        for relPath in members:
            print(relPath)
        print('\n%s Dateien, %s %s, Quelle: %s'
              % (len(members), addonId, version, quelle))
        return 0

    target = buildZip(PROJECT_ROOT, args.out_dir, addonId, version, members)
    verifyZip(target, addonId, members)
    size = os.path.getsize(target)
    print('%s' % target)
    print('%s Dateien, %.1f KiB, Wurzelordner %s/, Quelle: %s'
          % (len(members), size / 1024.0, addonId, quelle))
    return 0


if __name__ == '__main__':
    sys.exit(main())
