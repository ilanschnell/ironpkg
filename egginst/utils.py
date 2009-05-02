import sys
import os
from os.path import abspath, basename, dirname, exists, isdir, join


on_win = sys.platform.startswith('win')


_lsp = len(sys.prefix) + 1
def rel_prefix(path):
    return path[_lsp:]


_usr = 'EGG-INFO/usr/'
def dest_arc(arcname):
    """
    Given an archive name, which has to start with 'EGG-INFO/usr/', returns
    a tuple of destination directory and the absolute path to the destination
    itself.
    """
    assert arcname.startswith(_usr), arcname
    dst_dir = join(sys.prefix, dirname(arcname[len(_usr):]))
    return dst_dir, join(dst_dir, basename(arcname))


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
