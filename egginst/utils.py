import os
import shutil
from os.path import isdir, isfile, join


def pprint_fn_action(fn, action):
    """
    Pretty print the distribution name (filename) and an action, the width
    of the output corresponds to the with of the progress bar used by the
    function below.
    """
    print "%-56s %20s" % (fn, '[%s]' % action)


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
    try:
        if isfile(path):
            if verbose:
                print "Removing: %r (file)" % path
            os.unlink(path)
        elif isdir(path):
            if verbose:
                print "Removing: %r (directory)" % path
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
