import sys
import os
import shutil
from os.path import abspath, dirname, isdir, isfile, islink, join


on_win = sys.platform.startswith('win')


def rel_prefix(path):
    assert abspath(path).startswith(sys.prefix)
    return path[len(sys.prefix) + 1:]


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


def rm_rf(path, verbose=False):
    if not on_win and islink(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        if verbose:
            print "Removing: %r (link)" % path
        os.unlink(path)

    if isfile(path):
        if verbose:
            print "Removing: %r (file)" % path
        try:
            os.unlink(path)
        except WindowsError:
            pass

    if isdir(path):
        if verbose:
            print "Removing: %r (directory)" % path
        try:
            shutil.rmtree(path)
        except WindowsError:
            pass


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
