import sys
import os
import hashlib
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


def md5_file(path):
    """
    Returns the md5sum of the file (located at `path`) as a hexadecimal
    string of length 32.
    """
    data = open(path, 'rb').read()
    return hashlib.md5(data).hexdigest()
