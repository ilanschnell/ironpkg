import os
import sys
from os.path import basename, dirname, exists, islink, join

from utils import rel_prefix


def create_link(arcname, link):
    usr = 'EGG-INFO/usr/'
    assert arcname.startswith(usr), arcname
    dst = join(sys.prefix, arcname[len(usr):])

    # Create the destination directory if it does not exist.  In most cases
    # it will exist, but you never know.
    if not exists(dirname(dst)):
        os.makedirs(dirname(dst))

    # Note that we have to check if the destination is a link because
    # exists('/path/to/dead-link') will return False, although
    # islink('/path/to/dead-link') is True.
    if islink(dst) or exists(dst):
        print "Warning: %r already exists, unlinking" % rel_prefix(dst)
        os.unlink(dst)

    print "Creating: %s (link to %s)" % (rel_prefix(dst), link)
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
        egg.files.append(create_link(arcname, link))
