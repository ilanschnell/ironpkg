import os
import sys
from os.path import basename, dirname, exists, islink, join

from utils import rel_prefix, dest_arc


def create_link(arcname, link):
    dst_dir, dst = dest_arc(arcname)

    # Create the destination directory if it does not exist.  In most cases
    # it will exist, but you never know.
    if not exists(dst_dir):
        os.makedirs(dst_dir)

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
        if line.startswith("#"):
            continue

        arcname, link = line.split()
        if link == 'False':
            continue

        egg.files.append(create_link(arcname, link))
