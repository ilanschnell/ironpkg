import os
from os.path import dirname, isdir, join

from egginst.utils import rm_rf


verbose = False


def create_link(arcname, link, prefix):
    usr = 'EGG-INFO/usr/'
    assert arcname.startswith(usr), arcname
    dst = join(prefix, arcname[len(usr):])

    # Create the destination directory if it does not exist.  In most cases
    # it will exist, but you never know.
    if not isdir(dirname(dst)):
        os.makedirs(dirname(dst))

    rm_rf(dst, verbose)
    if verbose:
        print "Creating: %s (link to %s)" % (dst, link)
    os.symlink(link, dst)
    return dst


def create(egg):
    """
    Given the content of the EGG-INFO/inst/files_to_install.txt file,
    create/remove the links listed therein.
    """
    for line in egg.lines_from_arcname('EGG-INFO/inst/files_to_install.txt'):
        arcname, link = line.split()
        if link == 'False':
            continue
        egg.files.append(create_link(arcname, link, egg.prefix))
