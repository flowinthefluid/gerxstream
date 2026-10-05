# -*- coding: utf-8 -*-
"""Kodi must be able to discover updates for the repository add-on itself."""

import hashlib
import xml.etree.ElementTree as ET
import zipfile
import pytest

from tools import build_repo


@pytest.mark.parametrize('pages_url', [
    'https://gerxstream-db50a2.gitlab.io',
    'https://flowinthefluid.github.io/gerxstream/repo',
])
def test_repository_is_in_catalog_and_datadir(tmp_path, pages_url):
    output = tmp_path / 'public'
    build_repo.build(str(output), pages_url=pages_url)

    catalog_bytes = (output / 'addons.xml').read_bytes()
    catalog = ET.fromstring(catalog_bytes)
    resolver = catalog.find("addon[@id='script.module.resolveurl']")
    assert resolver is not None
    resolver_version = resolver.get('version')
    resolver_zip = output / 'zips' / 'script.module.resolveurl' / ('script.module.resolveurl-%s.zip' % resolver_version)
    assert resolver_zip.exists()

    repository = catalog.find("addon[@id='repository.gerxstream']")
    assert repository is not None
    assert repository.get('version') == '1.0.6'
    assert repository.find('./extension/dir/info').text == pages_url + '/catalog/addons.xml'
    assert repository.find('./extension/dir/checksum').text == pages_url + '/catalog/addons.xml.md5'
    assert hashlib.md5(catalog_bytes).hexdigest() == (output / 'addons.xml.md5').read_text()
    assert (output / 'catalog' / 'addons.xml').read_bytes() == catalog_bytes
    assert (output / 'catalog' / 'addons.xml.md5').read_text() == (output / 'addons.xml.md5').read_text()

    name = 'repository.gerxstream-1.0.6.zip'
    install_zip = output / name
    update_zip = output / 'zips' / 'repository.gerxstream' / name
    assert install_zip.read_bytes() == update_zip.read_bytes()
    index_html = (output / 'index.html').read_text(encoding='utf-8')
    assert name in index_html
    with zipfile.ZipFile(update_zip) as archive:
        assert archive.testzip() is None
        manifest = ET.fromstring(archive.read('repository.gerxstream/addon.xml'))
    assert manifest.get('version') == repository.get('version')
    assert manifest.find('./extension/dir/checksum').text == repository.find('./extension/dir/checksum').text
