import sys
import os
from os.path import abspath, basename, dirname, exists, isdir, join


on_win = sys.platform.startswith('win')

bin_dir = join(sys.prefix, 'Scripts' if on_win else 'bin')


def rel_prefix(path):
    if path.startswith(sys.prefix + '/'):
        return path[len(sys.prefix) + 1:]
    return path


def rmdir_er(dn):
    """
    Remove empty directories recursively.
    """
    for name in os.listdir(dn):
        path = join(dn, name)
        if isdir(path):
            rmdir_er(path)

    if not os.listdir(dn):
        os.rmdir(dn)
