import os
import sys
import random
import shutil
import string
from os.path import basename, isdir, isfile, join


chars = string.letters + string.digits


def mk_tmp_dir():
    tmp_dir = join(sys.prefix, '.tmp_ironpkg')
    try:
        shutil.rmtree(tmp_dir)
    except (WindowsError, IOError):
        pass
    if not isdir(tmp_dir):
        os.mkdir(tmp_dir)
    return tmp_dir


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
    if isfile(path):
        if verbose:
            print "Removing: %r (file)" % path
        try:
            os.unlink(path)
        except (WindowsError, IOError):
            tmp_dir = mk_tmp_dir()
            rand = ''.join(random.choice(chars) for x in xrange(10))
            os.rename(path, join(tmp_dir, '%s_%s' % (rand, basename(path))))
    elif isdir(path):
        if verbose:
            print "Removing: %r (directory)" % path
        shutil.rmtree(path)


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
