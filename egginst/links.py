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


def remove_link(arcname):
    dst_dir, dst =  dest_arc(arcname)
    if not islink(dst):
        print 'Warning: ignoring missing link %r' % rel_prefix(dst)
        return
    os.unlink(dst)


def from_data(content, remove=False):
    """
    Given the content of the EGG-INFO/inst/files_to_install.txt file,
    create/remove the links listed therein.
    """
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        arcname, link = line.split()
        if link == 'False':
            continue

        if remove:
            remove_link(arcname)
        else:
            create_link(arcname, link)
