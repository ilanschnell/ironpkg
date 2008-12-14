"""
This module is not part of the original setuptools code.

It was created because much of the code in order modules was (and still
is) unorganized and simple utility functions were defined as class methods
for no obious reason, uselessly cluttering some of the large classes.
This module is a place such functions.
"""
import shutil
from os import path
from distutils import log


try:
    from os import chmod as _chmod
except ImportError:
    # Jython compatibility
    def _chmod(*args):
        pass


def chmod(path, mode):
    log.debug("changing mode of %s to %o", path, mode)
    try:
        _chmod(path, mode)
    except os.error, e:
        log.debug("chmod failed: %s", e)


def rm_rf(file_or_dir):
    """
    Removes the file or directory (if it exists),
    returns 0 on success, 1 on failure.
    """
    if not path.exists(file_or_dir):
        return 0

    retcode = 0
    try:
        if path.isdir(file_or_dir):
            shutil.rmtree(file_or_dir)
        else:
            os.remove(file_or_dir)

    except (IOError, OSError), err :
        log.error("Error: could not remove %s: %s", file_or_dir, err)
        retcode = 1

    return retcode
