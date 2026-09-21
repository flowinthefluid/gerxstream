# -*- coding: utf-8 -*-
# Python 3
"""Baut den Inhalt des Hosting-Repos fuer die eigene GerXStream-Quelle.

Ziel ist die Struktur aus docs/REPO-SPEC.md: der Ordner `repo/`, den man in
den Branch `main` von https://github.com/flowinthefluid/gerxstream legt,
damit Kodi ihn als Addon-Repository lesen kann (Referenz: Aufbau von
K.U.S AllInOne Repository / anderer freier Kodi-Repos - ein Zeiger-Addon
`repository.<name>` plus `addons.xml`/`addons.xml.md5` plus `zips/`).

Enthaelt zwei Zeiger-Addons und das zum Start benoetigte Resolver-Modul:
    - repository.gerxstream    -> unsere eigene Quelle (dieses Repo)
    - repository.resolveurl    -> Zeiger auf Gujal00/smrzips (offizielles
        ResolveURL-Repo). Wird nur mitgehostet, damit Nutzer ResolveURL ohne
        Odyssee ueber unsere eigene Quelle installieren koennen (Befund D1 /
        REPO-SPEC.md Abschnitt 5). Wir bauen ResolveURL nicht selbst; der Zeiger
        laedt weiterhin direkt von Gujal00.
    - script.module.resolveurl -> die verifizierte Upstream-Version wird in
        den eigenen Katalog gespiegelt, damit Kodi sie als Abhaengigkeit von
        GerXStream in derselben Aktualisierung aufloesen kann.

Aufruf aus dem Projektverzeichnis:

    python tools/build_repo.py

Optionen:
    --out-dir DIR   Zielverzeichnis (Vorgabe: dist/gerxstream-repo)
"""

import argparse
import hashlib
import os
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from urllib.request import urlopen

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_release  # noqa: E402  (Nachbarskript, siehe tools/build_release.py)

REPO_ADDONS = ('repository.gerxstream', 'repository.resolveurl')
RESOLVEURL_ID = 'script.module.resolveurl'
RESOLVEURL_VERSION = '5.1.209'
RESOLVEURL_ZIP_URL = ('https://raw.githubusercontent.com/Gujal00/smrzips/master/'
                      'zips/script.module.resolveurl/'
                      'script.module.resolveurl-%s.zip' % RESOLVEURL_VERSION)
RESOLVEURL_LICENSE_URL = 'https://raw.githubusercontent.com/Gujal00/ResolveURL/master/LICENSE'


def readAddonXml(path):
    node = ET.parse(path).getroot()
    return node.get('id'), node.get('version')


def stripXmlDeclaration(xmlText):
    stripped = xmlText.lstrip()
    if stripped.startswith('<?xml'):
        return stripped.split('?>', 1)[1].strip()
    return stripped.strip()


def buildPointerZip(sourceDir, addonId, version, outDir):
    """Zippt ein kleines Zeiger-Addon (nur addon.xml + Bilder)."""
    os.makedirs(outDir, exist_ok=True)
    target = os.path.join(outDir, '%s-%s.zip' % (addonId, version))
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for fileName in sorted(os.listdir(sourceDir)):
            absPath = os.path.join(sourceDir, fileName)
            if os.path.isfile(absPath):
                archive.write(absPath, '%s/%s' % (addonId, fileName))
    return target


def copyAddonAssets(sourceDir, targetDir):
    os.makedirs(targetDir, exist_ok=True)
    for fileName in sorted(os.listdir(sourceDir)):
        srcPath = os.path.join(sourceDir, fileName)
        if os.path.isfile(srcPath):
            shutil.copy2(srcPath, os.path.join(targetDir, fileName))


def mirrorResolveUrl(outZipsDir):
    """Spiegelt die fest verdrahtete GPL-2.0-ResolveURL-Version in den Katalog.

    Das Repository verweist damit nicht auf einen fluechtigen GitHub-Zipball:
    Kodi bekommt ein normales, versionsgeprueftes Add-on-Paket. Die Pruefung
    verhindert, dass eine geaenderte Upstream-Antwort unter demselben Pfad in
    unser Repository gelangt.
    """
    targetDir = os.path.join(outZipsDir, RESOLVEURL_ID)
    os.makedirs(targetDir, exist_ok=True)
    targetZip = os.path.join(targetDir, '%s-%s.zip' %
                             (RESOLVEURL_ID, RESOLVEURL_VERSION))

    with urlopen(RESOLVEURL_ZIP_URL, timeout=30) as response:
        archiveBytes = response.read()
    with open(targetZip, 'wb') as fh:
        fh.write(archiveBytes)

    with zipfile.ZipFile(targetZip, 'r') as archive:
        addonPath = '%s/addon.xml' % RESOLVEURL_ID
        if addonPath not in archive.namelist():
            raise RuntimeError('ResolveURL-Paket enthaelt kein %s' % addonPath)
        root = ET.fromstring(archive.read(addonPath))
        if root.get('id') != RESOLVEURL_ID or root.get('version') != RESOLVEURL_VERSION:
            raise RuntimeError('ResolveURL-Paket stimmt nicht mit %s %s ueberein' %
                               (RESOLVEURL_ID, RESOLVEURL_VERSION))

        for filename in ('addon.xml', 'changelog.txt', 'icon.png', 'fanart.jpg'):
            member = '%s/%s' % (RESOLVEURL_ID, filename)
            if member in archive.namelist():
                with open(os.path.join(targetDir, filename), 'wb') as fh:
                    fh.write(archive.read(member))

    # GPL-2.0-Hinweis fuer die mitgelieferte Drittanbieter-Komponente.
    with urlopen(RESOLVEURL_LICENSE_URL, timeout=30) as response:
        licenseText = response.read()
    with open(os.path.join(targetDir, 'LICENSE.GPL-2.0.txt'), 'wb') as fh:
        fh.write(licenseText)
    return os.path.join(targetDir, 'addon.xml')


def buildAddonsXml(addonXmlPaths, outDir):
    blocks = [stripXmlDeclaration(open(p, 'r', encoding='utf-8').read()) for p in addonXmlPaths]
    content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n%s\n</addons>\n' % (
        '\n'.join(blocks))
    addonsXmlPath = os.path.join(outDir, 'addons.xml')
    with open(addonsXmlPath, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(content)
    digest = hashlib.md5(content.encode('utf-8')).hexdigest()
    with open(os.path.join(outDir, 'addons.xml.md5'), 'w', encoding='utf-8', newline='') as fh:
        fh.write(digest)
    return addonsXmlPath


def buildIndex(repoVersion, outDir):
    """Erzeugt eine Kodi-lesbare Liste fuer die Repository-ZIP."""
    content = '''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GerXStream Kodi-Repository</title>
</head>
<body>
  <h1>Index of /gerxstream/repo/</h1>
  <a href="repository.gerxstream-%s.zip">repository.gerxstream-%s.zip</a><br>
</body>
</html>
''' % (repoVersion, repoVersion)
    with open(os.path.join(outDir, 'index.html'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Baut den Hosting-Repo-Ordner fuer gerxstream/repo.')
    parser.add_argument('--out-dir', default=os.path.join(PROJECT_ROOT, 'dist', 'gerxstream-repo'),
                        help='Zielverzeichnis (Vorgabe: dist/gerxstream-repo)')
    args = parser.parse_args(argv)

    outDir = args.out_dir
    if os.path.isdir(outDir):
        shutil.rmtree(outDir)
    os.makedirs(outDir)
    zipsDir = os.path.join(outDir, 'zips')

    # 1. Plugin-Zip (wie tools/build_release.py, aber direkt in zips/ abgelegt)
    pluginId, pluginVersion = build_release.readAddonMetadata(PROJECT_ROOT)
    members, _fromGit = build_release.collectFiles(PROJECT_ROOT)
    pluginZipDir = os.path.join(zipsDir, pluginId)
    pluginZipPath = build_release.buildZip(PROJECT_ROOT, pluginZipDir, pluginId, pluginVersion, members)
    build_release.verifyZip(pluginZipPath, pluginId, members)
    for assetName in ('addon.xml', 'changelog.txt'):
        shutil.copy2(os.path.join(PROJECT_ROOT, assetName), os.path.join(pluginZipDir, assetName))
    for assetName in ('icon.png', 'fanart.jpg', 'banner.png', 'clearlogo.png'):
        assetPath = os.path.join(PROJECT_ROOT, 'resources', assetName)
        if os.path.isfile(assetPath):
            shutil.copy2(assetPath, os.path.join(pluginZipDir, assetName))

    # 2. Zeiger-Addons: repository.gerxstream + repository.resolveurl
    addonXmlPaths = [os.path.join(PROJECT_ROOT, 'addon.xml')]
    for repoId in REPO_ADDONS:
        sourceDir = os.path.join(PROJECT_ROOT, repoId)
        _id, version = readAddonXml(os.path.join(sourceDir, 'addon.xml'))
        pointerZipDir = os.path.join(zipsDir, repoId)
        buildPointerZip(sourceDir, repoId, version, pointerZipDir)
        copyAddonAssets(sourceDir, pointerZipDir)
        if repoId == 'repository.gerxstream':
            buildIndex(version, pointerZipDir)
        addonXmlPaths.append(os.path.join(sourceDir, 'addon.xml'))

    # 3. ResolveURL direkt in diesem Katalog, damit die zwingende Abhaengigkeit
    # beim Installieren von GerXStream verfuegbar ist.
    addonXmlPaths.append(mirrorResolveUrl(zipsDir))

    # repository.gerxstream steht zusaetzlich installierbar an der Wurzel,
    # so wie Kodi-Repos das ueblicherweise anbieten (siehe K.U.S-Referenz).
    gerxstreamRepoDir = os.path.join(PROJECT_ROOT, 'repository.gerxstream')
    _id, repoVersion = readAddonXml(os.path.join(gerxstreamRepoDir, 'addon.xml'))
    buildPointerZip(gerxstreamRepoDir, 'repository.gerxstream', repoVersion, outDir)
    # Die Medienquelle zeigt direkt auf repo/. Darum liegen die Dateien des
    # Repository-Addons zusaetzlich dort - nicht nur unter zips/.
    copyAddonAssets(gerxstreamRepoDir, outDir)
    copyAddonAssets(gerxstreamRepoDir, os.path.join(outDir, 'repository.gerxstream'))
    buildIndex(repoVersion, outDir)

    # 4. addons.xml + addons.xml.md5 ueber alle Addons
    buildAddonsXml(addonXmlPaths, outDir)

    print('Hosting-Ordner: %s' % outDir)
    print('Enthaelt: addons.xml, addons.xml.md5, repository.gerxstream(-%s.zip), '
            'zips/plugin.video.gerxstream, zips/repository.gerxstream, '
            'zips/repository.resolveurl, zips/script.module.resolveurl' % repoVersion)
    print('Naechster Schritt: Inhalt in repo/ auf Branch main von '
          'https://github.com/flowinthefluid/gerxstream committen und pushen.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
