# Copyright (c) 2008-2009 by Enthought, Inc.
# All rights reserved.

import os
import sys

from distutils.sysconfig import get_python_lib
from os.path import abspath, expanduser, isfile, join

from enstaller import __version__
from utils import PY_VER


CONFIG_FN = ".enstaller4rc"
HOME_CONFIG_PATH = abspath(expanduser("~/" + CONFIG_FN))
SYSTEM_CONFIG_PATH = join(get_python_lib(), CONFIG_FN)


def get_path():
    """
    Return the absolute path to our config file.
    """
    if isfile(HOME_CONFIG_PATH):
        return HOME_CONFIG_PATH

    if isfile(SYSTEM_CONFIG_PATH):
        return SYSTEM_CONFIG_PATH

    return None


def input_openid(epd_repo):
    import time
    import urllib2

    print """\
Welcome to Enstaller (version %s)!

In order to access the EPD repository, please enter
the OpenID which you use to subscribe to EPD.
If you are not subscribed to EPD, hit Return.
""" % __version__
    while True:
        openid = raw_input('OpenID: ').strip()
        if not openid:
            return ''
        print "You have entered:", openid
        tmp = raw_input("Correct? [y/n]: ")
        if tmp.lower() in ('y', 'yes'):
            break
    print "Authenticating..."
    fi = urllib2.urlopen('http://www.enthought.com/')
    data = fi.read()
    fi.close()
    time.sleep(0.75)
    print "EPD repo url:", epd_repo
    time.sleep(0.75)
    return openid

RC_TMPL = """\
# Enstaller configuration file
# ============================
#
# This file contains the default package repositories used by
# Enstaller (version 4) for Python %(py_ver)s installed in:
#
#     %(prefix)s
#
# This file was created by initially running the enpkg command.

# EPD subscriber OpenID:
%(openid_line)s

# This list of repositories may include the EPD repository.  However,
# if the EPD repository is listed here things will only work if the
# correct EPD subscriber OpenID is provided above.  Notice also that
# only indexed repositories, i.e. HTTP directories which contain a file
# 'index-depend.bz2', can be listed here.
IndexedRepos = %(repos)s
"""

def write():
    """
    Return the default state of this project's config file.
    """
    try:
        import custom_tools
    except ImportError:
        custom_tools = None

    # If user is 'root', then create the config file in the system
    # site-packages.  Otherwise, create it in the user's HOME directory.
    if sys.platform != 'win32' and os.getuid() == 0:
        path = SYSTEM_CONFIG_PATH
    else:
        path = HOME_CONFIG_PATH

    epd_repo = None
    if (custom_tools and hasattr(custom_tools, 'epd_baseurl') and
                         hasattr(custom_tools, 'epd_subdir')):
        epd_repo = custom_tools.epd_baseurl + custom_tools.epd_subdir + '/'

    openid = ''
    if epd_repo:
        openid = input_openid(epd_repo)

    repos = '[]'
    if openid:
        repos = '[\n    %r,\n]' % epd_repo

    py_ver = PY_VER
    prefix = sys.prefix
    if openid:
        openid_line = "EPD_OpenID = %r" % openid
    else:
        openid_line = "#EPD_OpenID = ''"

    fo = open(path, 'w')
    fo.write(RC_TMPL % locals())
    fo.close()
    print "Wrote configuration file:", path
    print 77 * '='


def read():
    """
    Return the current configuration as a dictionary, or None if the
    configuration file does not exist:
    """
    if hasattr(read, 'cache'):
        return read.cache

    path = get_path()
    if not path:
        return None
    d = {}
    execfile(path, d)
    read.cache = {}
    for k in ['EPD_OpenID', 'IndexedRepos', 'LOCAL']:
        if d.has_key(k):
            read.cache[k] = d[k]
    return read()


if __name__ == '__main__':
    write()
    print read()
