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
    assert repository.get('version') == '1.0.8'
    assert repository.find('./extension/dir/info').text == pages_url + '/catalog/addons.xml'
    assert repository.find('./extension/dir/checksum').text == pages_url + '/catalog/addons.xml.md5'
    assert hashlib.md5(catalog_bytes).hexdigest() == (output / 'addons.xml.md5').read_text()
    assert (output / 'catalog' / 'addons.xml').read_bytes() == catalog_bytes
    assert (output / 'catalog' / 'addons.xml.md5').read_text() == (output / 'addons.xml.md5').read_text()

    plugin = catalog.find("addon[@id='plugin.video.gerxstream']")
    assert plugin.get('version') == '1.0.38'
    plugin_zip = output / 'zips' / 'plugin.video.gerxstream' / 'plugin.video.gerxstream-1.0.38.zip'
    with zipfile.ZipFile(plugin_zip) as archive:
        assert archive.testzip() is None
        plugin_manifest = ET.fromstring(archive.read('plugin.video.gerxstream/addon.xml'))
        settings = ET.fromstring(archive.read('plugin.video.gerxstream/resources/settings.xml'))
        random_movies = archive.read('plugin.video.gerxstream/resources/lib/randommovies.py').decode('utf-8')
        rocketbeans = archive.read('plugin.video.gerxstream/sites/rocketbeans.py').decode('utf-8')
    assert plugin_manifest.get('version') == plugin.get('version')
    assert 'def showSeasons(' in rocketbeans
    assert 'def login(' in rocketbeans
    account = settings.find(".//category[@id='account']/group[@id='rocketbeansacc']")
    assert account is not None
    assert 'site=rocketbeans&function=login' in account.find("setting[@id='rocketbeans.login']/data").text
    assert 'def sampleCatalog(' in random_movies
    assert settings.find(".//category[@id='randommovies']//setting[@id='randomMinImdb']") is not None
    assert settings.find(".//category[@id='categories']//setting[@id='categoryMinImdb']") is not None
    for setting_id in ('actorPeopleSort', 'directorPeopleSort'):
        setting = settings.find(".//setting[@id='%s']" % setting_id)
        assert setting.find('default').text == 'inherit'
        assert setting.find('constraints/options/option').text == 'inherit'

    name = 'repository.gerxstream-1.0.8.zip'
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
