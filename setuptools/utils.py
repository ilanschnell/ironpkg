"""
This module is not part of the original setuptools code.

It was created because much of the code in order modules was (and still
is) unorganized and simple utility functions were defined as class methods
for no obious reason, uselessly cluttering some of the large classes.
This module is a place such functions.
"""
import os
import sys
import subprocess
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


def execute_script(py_path):
    """
    Execute the python script (located at path) and log error message
    when the return value of the subprocess was non-zero.
    """
    retcode = subprocess.call([sys.executable, py_path])

    if retcode != 0:
        log.warn("WARNING: executing Python script %r returned %i",
                 py_path, retcode)


def samefile(p1, p2):
    """
    Similar as os.path.samefile
    
    Note:
        Only on Macintosh and Unix is the function os.path.samefile available.
    """
    if(hasattr(os.path, 'samefile') and
       os.path.exists(p1) and
       os.path.exists(p2)
       ):
        return os.path.samefile(p1,p2)

    return bool(os.path.normpath(os.path.normcase(p1)) ==
                os.path.normpath(os.path.normcase(p2)))
