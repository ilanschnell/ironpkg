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


def human_bytes(n):
    """
    Return the number of bytes n in more human readable form.
    """
    if n < 1024:
        return '%i B' % n

    k = (n - 1) / 1024 + 1
    if k < 1024:
        return '%i KB' % k

    return '%.2f MB' % (float(n) / (2**20))
