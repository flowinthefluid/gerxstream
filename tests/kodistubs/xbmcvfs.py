# -*- coding: utf-8 -*-
import os
_ROOT = os.environ.get('GXS_PROFILE', '/tmp/gxs-test-profile')


def translatePath(path):
    if path.startswith('special://'):
        return os.path.join(_ROOT, path.split('://', 1)[1])
    return path
