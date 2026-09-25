# -*- coding: utf-8 -*-
"""Small defensive helpers for endpoints that are expected to return JSON."""

import json

from resources.lib.tools import logger


def loadResponse(content, siteName, url=''):
    """Decode a JSON response without surfacing HTML error pages as tracebacks."""
    if not content or not isinstance(content, (str, bytes, bytearray)):
        return None
    try:
        decoded = json.loads(content)
    except (TypeError, ValueError) as error:
        logger.info('-> [%s]: erwartete JSON-Antwort nicht erhalten (%s): %s'
                    % (siteName, error.__class__.__name__, url))
        return None
    return decoded
