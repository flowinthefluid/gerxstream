# -*- coding: utf-8 -*-
"""Kodi must be able to discover updates for the repository add-on itself."""

import hashlib
import xml.etree.ElementTree as ET
import zipfile

from tools import build_repo


def test_gitlab_repository_is_in_catalog_and_datadir(tmp_path):
    output = tmp_path / 'public'
    build_repo.build(str(output), pages_url='https://example.gitlab.io/')

    catalog_bytes = (output / 'addons.xml').read_bytes()
    catalog = ET.fromstring(catalog_bytes)
    repository = catalog.find("addon[@id='repository.gerxstream']")
    assert repository is not None
    assert repository.get('version') == '1.0.4'
    assert repository.find('./extension/dir/info').text == 'https://example.gitlab.io/addons.xml'
    assert hashlib.md5(catalog_bytes).hexdigest() == (output / 'addons.xml.md5').read_text()

    name = 'repository.gerxstream-1.0.4.zip'
    install_zip = output / name
    update_zip = output / 'zips' / 'repository.gerxstream' / name
    assert install_zip.read_bytes() == update_zip.read_bytes()
    with zipfile.ZipFile(update_zip) as archive:
        assert archive.testzip() is None
        manifest = ET.fromstring(archive.read('repository.gerxstream/addon.xml'))
    assert manifest.get('version') == repository.get('version')
