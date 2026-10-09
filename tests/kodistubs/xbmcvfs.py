# -*- coding: utf-8 -*-
import os
_ROOT = os.environ.get('GXS_PROFILE', '/tmp/gxs-test-profile')


def exists(path):
    return os.path.exists(translatePath(path))


class File:
    def __init__(self, path, mode='r'):
        self.handle = open(translatePath(path), mode, encoding='utf-8')

    def read(self, length=0):
        return self.handle.read(length or -1)

    def write(self, content):
        self.handle.write(content)
        return True

    def close(self):
        self.handle.close()


def translatePath(path):
    if path.startswith('special://'):
        return os.path.join(_ROOT, path.split('://', 1)[1])
    return path
