#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Portabler Repository-Build fuer GerXStream (Python, ohne xmllint/zip-Binary).

Erzeugt dieselben Artefakte wie tools/build-gitlab-pages.sh, aber
plattformunabhaengig und CI-tauglich (GitHub Actions). Standard-Ausgabe ist
``dist/`` - die GitLab-Pages-Auslieferung in ``public/`` bleibt unberuehrt, es
gibt also keine zwei Schreiber auf demselben Verzeichnis.

Beispiele:
    python3 tools/build_repo.py                 # Build nach dist/
    python3 tools/build_repo.py --bump patch    # Version erhoehen + Build
    python3 tools/build_repo.py --pages-url https://user.gitlab.io/proj
"""

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Exakt die Laufzeitdateien, die auch der Shell-Build ausliefert (keine
# Entwicklungs-/Testdateien: tests/, docs/, tools/ bleiben aussen vor).
PLUGIN_PAYLOAD = ('addon.xml', 'default.py', 'gerxstream.py', 'service.py',
                  'changelog.txt', 'license.txt', 'resources', 'sites')
ASSETS = ('icon.png', 'fanart.jpg', 'banner.png', 'clearlogo.png')
RESOLVER_ID = 'script.module.resolveurl'
REPO_ID = 'repository.gerxstream'


def _addon_field(addon_xml, attr):
    root = ET.parse(addon_xml).getroot()
    return root.get(attr)


def _strip_xml_decl(text):
    lines = text.splitlines(keepends=True)
    if lines and lines[0].lstrip().startswith('<?xml '):
        return ''.join(lines[1:])
    return text


def bump_version(version, part):
    major, minor, patch = (int(x) for x in version.split('.')[:3])
    if part == 'major':
        major, minor, patch = major + 1, 0, 0
    elif part == 'minor':
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return '%d.%d.%d' % (major, minor, patch)


def apply_bump(old, new):
    """Version in addon.xml, im Shell-Guard und im Changelog nachziehen."""
    addon_xml = os.path.join(PROJECT_DIR, 'addon.xml')
    text = open(addon_xml, encoding='utf-8').read()
    text = text.replace('version="%s"' % old, 'version="%s"' % new, 1)
    open(addon_xml, 'w', encoding='utf-8').write(text)

    # Shell-Build pinnt die Version als Sicherheitsnetz - mitziehen.
    shell = os.path.join(PROJECT_DIR, 'tools', 'build-gitlab-pages.sh')
    if os.path.exists(shell):
        s = open(shell, encoding='utf-8').read().replace(old, new)
        open(shell, 'w', encoding='utf-8').write(s)

    changelog = os.path.join(PROJECT_DIR, 'changelog.txt')
    if os.path.exists(changelog):
        prev = open(changelog, encoding='utf-8').read()
        open(changelog, 'w', encoding='utf-8').write('[B]%s[/B]\n- Build\n\n%s' % (new, prev))
    print('Version %s -> %s' % (old, new))


def _zip_dir(src_root, arcname_root, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for base, _dirs, files in os.walk(src_root):
            if '__pycache__' in base:
                continue
            for name in files:
                if name.endswith(('.pyc', '.pyo')):
                    continue
                full = os.path.join(base, name)
                rel = os.path.relpath(full, src_root)
                zf.write(full, os.path.join(arcname_root, rel))


def build(out_dir, pages_url=None, force=False):
    addon_xml = os.path.join(PROJECT_DIR, 'addon.xml')
    addon_id = _addon_field(addon_xml, 'id')
    version = _addon_field(addon_xml, 'version')
    print('Baue %s %s -> %s' % (addon_id, version, out_dir))

    if os.path.exists(out_dir):
        if not force:
            sys.exit('Ausgabeverzeichnis existiert: %s (--force zum Ueberschreiben)' % out_dir)
        shutil.rmtree(out_dir)
    zips_dir = os.path.join(out_dir, 'zips', addon_id)
    os.makedirs(zips_dir)

    with tempfile.TemporaryDirectory() as tmp:
        payload = os.path.join(tmp, addon_id)
        os.makedirs(payload)
        for entry in PLUGIN_PAYLOAD:
            src = os.path.join(PROJECT_DIR, entry)
            if not os.path.exists(src):
                sys.exit('Fehlende Laufzeitdatei: %s' % entry)
            dst = os.path.join(payload, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            else:
                shutil.copy2(src, dst)
        _zip_dir(payload, addon_id, os.path.join(zips_dir, '%s-%s.zip' % (addon_id, version)))

    # Sidecar-Metadaten + Assets (vor der Installation lesbar).
    shutil.copy2(addon_xml, os.path.join(zips_dir, 'addon.xml'))
    for extra in ('changelog.txt',):
        p = os.path.join(PROJECT_DIR, extra)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(zips_dir, extra))
    res_out = os.path.join(zips_dir, 'resources')
    os.makedirs(res_out, exist_ok=True)
    for asset in ASSETS:
        a = os.path.join(PROJECT_DIR, 'resources', asset)
        if os.path.exists(a):
            shutil.copy2(a, os.path.join(res_out, asset))

    # Repository-ZIP sowohl als direkte Installationsdatei als auch im
    # datadir ablegen. Nur letzterer Pfad kann Kodi selbst aktualisieren.
    repository_manifest = None
    tmpl = os.path.join(PROJECT_DIR, REPO_ID, 'addon.xml.in')
    if pages_url and os.path.exists(tmpl):
        rurl = pages_url.rstrip('/')
        with tempfile.TemporaryDirectory() as tmp:
            rp = os.path.join(tmp, REPO_ID)
            os.makedirs(rp)
            repository_manifest = open(tmpl, encoding='utf-8').read().replace('@PAGES_URL@', rurl)
            with open(os.path.join(rp, 'addon.xml'), 'wb') as fh:
                fh.write(repository_manifest.encode('utf-8'))
            for asset in ('icon.png', 'fanart.jpg'):
                shutil.copy2(os.path.join(PROJECT_DIR, 'resources', asset), os.path.join(rp, asset))
            repo_ver = _addon_field(os.path.join(rp, 'addon.xml'), 'version')
            repo_dir = os.path.join(out_dir, 'zips', REPO_ID)
            os.makedirs(repo_dir)
            repo_zip = '%s-%s.zip' % (REPO_ID, repo_ver)
            _zip_dir(rp, REPO_ID, os.path.join(repo_dir, repo_zip))
            shutil.copy2(os.path.join(repo_dir, repo_zip), os.path.join(out_dir, repo_zip))
            for asset in ('addon.xml', 'icon.png', 'fanart.jpg'):
                shutil.copy2(os.path.join(rp, asset), os.path.join(repo_dir, asset))
        print('Repository-Pointer gebaut (Pages-URL: %s)' % rurl)

    # addons.xml zusammensetzen (Format identisch zum Shell-Build).
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n']
    resolver_xml = os.path.join(PROJECT_DIR, 'public', 'zips', RESOLVER_ID, 'addon.xml')
    if os.path.exists(resolver_xml):
        parts.append(_strip_xml_decl(open(resolver_xml, encoding='utf-8').read()))
        if not parts[-1].endswith('\n'):
            parts.append('\n')
    parts.append(_strip_xml_decl(open(addon_xml, encoding='utf-8').read()))
    if not parts[-1].endswith('\n'):
        parts.append('\n')
    if repository_manifest:
        parts.append(_strip_xml_decl(repository_manifest))
        if not parts[-1].endswith('\n'):
            parts.append('\n')
    parts.append('</addons>\n')
    addons_xml = ''.join(parts)
    # Hash exactly the bytes served to Kodi. Text mode would translate LF to
    # CRLF on Windows and produce a checksum for different file contents.
    addons_bytes = addons_xml.encode('utf-8')
    with open(os.path.join(out_dir, 'addons.xml'), 'wb') as fh:
        fh.write(addons_bytes)
    md5 = hashlib.md5(addons_bytes).hexdigest()
    with open(os.path.join(out_dir, 'addons.xml.md5'), 'w', encoding='utf-8') as fh:
        fh.write(md5)  # ohne abschliessenden Zeilenumbruch (wie der Shell-Build)

    # Kodi can cache the installation page as a directory listing containing
    # only ZIPs. Its file opener then rejects other files in that directory.
    catalog_dir = os.path.join(out_dir, 'catalog')
    os.makedirs(catalog_dir)
    for name in ('addons.xml', 'addons.xml.md5'):
        shutil.copy2(os.path.join(out_dir, name), os.path.join(catalog_dir, name))

    print('Fertig. addons.xml.md5 = %s' % md5)


def main(argv=None):
    ap = argparse.ArgumentParser(description='GerXStream Repository-Build')
    ap.add_argument('--out', default=os.path.join(PROJECT_DIR, 'dist'))
    ap.add_argument('--bump', choices=('patch', 'minor', 'major'))
    ap.add_argument('--pages-url', default=os.environ.get('PAGES_URL'))
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args(argv)

    if args.bump:
        old = _addon_field(os.path.join(PROJECT_DIR, 'addon.xml'), 'version')
        apply_bump(old, bump_version(old, args.bump))
    build(args.out, pages_url=args.pages_url, force=args.force)


if __name__ == '__main__':
    main()
