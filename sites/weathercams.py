# -*- coding: utf-8 -*-
# Python 3
"""Kuratiertes Verzeichnis oeffentlich zugaenglicher Live-Webcams.

Die Quelle ist absichtlich kein Wetterdienst: Sie liefert weder Messwerte
noch Vorhersagen. Der Katalog ist von der Providerlogik getrennt in
resources/data/webcams.json abgelegt. Damit kann er von wenigen auf viele
tausend Eintraege wachsen, ohne dass Navigation und Playercode kopiert werden
muessen.
"""

import json
import os

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.gui.gui import cGui
from resources.lib.config import cConfig
from resources.lib.tools import logger


SITE_IDENTIFIER = 'weathercams'
SITE_NAME = 'Webcam-Katalog'
CONTENT_CATEGORIES = ('live',)
SITE_GLOBAL_SEARCH = False
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)


def _catalogPath():
    return os.path.join(
        cConfig().getAddonInfo('path'), 'resources', 'data', 'webcams.json')


def _catalog():
    """Liest den versionierten Webcam-Katalog defensiv ein."""
    try:
        with open(_catalogPath(), 'r', encoding='utf-8') as catalogFile:
            catalog = json.load(catalogFile)
    except (IOError, ValueError) as error:
        logger.error('Webcam catalog could not be loaded: %s' % error)
        return {'categories': [], 'cameras': []}

    categories = catalog.get('categories', [])
    cameras = catalog.get('cameras', [])
    if not isinstance(categories, list) or not isinstance(cameras, list):
        logger.error('Webcam catalog has an invalid structure')
        return {'categories': [], 'cameras': []}
    return {'categories': categories, 'cameras': cameras}


def _camerasForCategory(categoryId=None):
    cameras = _catalog()['cameras']
    if categoryId:
        cameras = [camera for camera in cameras
                   if camera.get('category') == categoryId]
    # Jede Zeile muss eine explizite Betreiberquelle und einen finalen,
    # direkt abspielbaren Stream besitzen. So gelangen keine Suchtreffer,
    # privaten Kameras oder HTML-Player in die Wiedergabe.
    return [camera for camera in cameras
            if camera.get('id') and camera.get('title')
            and camera.get('stream') and camera.get('source_url')]


def _cameraById(cameraId):
    for camera in _camerasForCategory():
        if camera['id'] == cameraId:
            return camera
    return None


def load():
    """Listet Webcam-Kategorien statt einer unwartbaren Gesamtliste."""
    logger.info('Load %s' % SITE_NAME)
    oGui = cGui()
    catalog = _catalog()
    cameras = _camerasForCategory()
    counts = {}
    for camera in cameras:
        categoryId = camera.get('category')
        counts[categoryId] = counts.get(categoryId, 0) + 1

    categories = [category for category in catalog['categories']
                  if category.get('id') in counts]
    total = len(categories)
    for category in categories:
        params = ParameterHandler()
        categoryId = category['id']
        params.setParam('category', categoryId)
        title = '%s (%d)' % (category.get('title', categoryId), counts[categoryId])
        oGuiElement = cGuiElement(title, SITE_IDENTIFIER, 'listCategory')
        oGuiElement.setDescription(category.get('description', ''))
        oGui.addFolder(oGuiElement, params, True, total)
    oGui.setEndOfDirectory()


def listCategory():
    """Listet die abspielbaren Kameras einer Kategorie."""
    categoryId = ParameterHandler().getValue('category')
    cameras = _camerasForCategory(categoryId)
    oGui = cGui()
    total = len(cameras)
    for camera in cameras:
        params = ParameterHandler()
        params.setParam('cameraId', camera['id'])
        oGuiElement = cGuiElement(camera['title'], SITE_IDENTIFIER, 'showHosters')
        details = [camera.get('description', '')]
        location = ', '.join(filter(None, (camera.get('city'), camera.get('country'))))
        if location:
            details.append('Ort: %s' % location)
        details.append('Quelle: %s' % camera.get('operator', camera['source_url']))
        details.append('Geprueft: %s' % camera.get('verified_at', 'unbekannt'))
        oGuiElement.setDescription('\n'.join(details))
        oGuiElement.setInfo('LIVE')
        # Ein nicht als Ordner markierter Eintrag startet ueber den normalen
        # Hoster-Weg. Das setzt inputstream.adaptive fuer HLS und behandelt
        # die Webcam wie jeden anderen direkten Medienstrom.
        oGui.addFolder(oGuiElement, params, False, total)
    oGui.setEndOfDirectory()


def showHosters():
    """Uebergibt einen im Katalog hinterlegten HLS-Feed an den Player."""
    camera = _cameraById(ParameterHandler().getValue('cameraId'))
    if not camera:
        return []
    return [
        {'link': camera['stream'], 'name': 'HLS', 'displayedName': 'HLS-Livestream'},
        'getHosterUrl',
    ]


def getHosterUrl(sUrl=False):
    """HLS ist bereits eine finale Medienadresse und braucht ResolveURL nicht."""
    if not sUrl:
        return []
    return [{'streamUrl': sUrl, 'resolved': True}]
