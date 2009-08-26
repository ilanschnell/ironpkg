# Copyright (c) 2008-2009 by Enthought, Inc.
# All rights reserved.

import os
import stat
import sys

from distutils.sysconfig import get_python_lib
from os.path import abspath, expanduser, isfile, join

from enstaller import __version__


CONFIG_FN = ".enstaller4rc"
HOME_CONFIG_PATH = abspath(expanduser("~/" + CONFIG_FN))
SYSTEM_CONFIG_PATH = abspath(join(get_python_lib(), CONFIG_FN))


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
    print """\
Welcome to Enstaller (version %s)!

Please enter your OpenID which you use to subscribe to EPD.
If you are not subscribed to EPD, please hit Return.
""" % __version__
    while True:
        openid = raw_input('OpenID: ').strip()
        if not openid:
            return ''
        print "You have entered:", openid
        tmp = raw_input("Correct? [y/n]: ")
        if tmp.lower().startswith('y'):
            break
    print 70 * '=' + """
Welcome to the EPD subscriber repository!
The package repository for your install of EPD is located:

    %s

Your OpenID and this URL are stored in the Enstaller configuration file,
which may be change at any point by editing the file, see the configuration
file for more details.
""" % epd_repo
    return openid


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
        epd_repo = custom_tools.epd_baseurl + custom_tools.epd_subdir +'/'

    openid = ''
    if epd_repo:
        openid = input_openid(epd_repo)

    repos = '[]'
    if openid:
        repos = '[\n    %r,\n]' % epd_repo

    py_ver = sys.version[:3]
    prefix = sys.prefix
    if openid:
        openid_line = "EPD_OpenID = %r" % openid
    else:
        openid_line = "#EPD_OpenID = ''"

    fo = open(path, 'w')
    fo.write("""\
# Enstaller configuration file
# ============================
#
# This file contains the default package repositories used by
# Enstaller (version 4) for Python %(py_ver)s installed in:
#
#     %(prefix)s
#
# This file created by initially running the enpkg command.

# EPD subscriber OpenID:
%(openid_line)s


# This list of repositories may include the EPD repository.  However,
# if the EPD repository is listed here things will only work if the
# correct EPD subscriber OpenID is provided above.
IndexedRepos = %(repos)s


# Setuptools (easy_install) repositories, the index URL is specified by
# appending a ',index' to the end of a URL.  There can only be one index
# listed here and when this file is created by default the index is set to
# the PyPI index.
SetuptoolsRepos = [
    'http://pypi.python.org/simple,index',  # Python Package Index
]
""" % locals())
    fo.close()
    print "Wrote configuration file:", path
    print 70 * '='


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
    for k in ['EPD_OpenID', 'IndexedRepos', 'SetuptoolsRepos', 'LOCAL']:
        if d.has_key(k):
            read.cache[k] = d[k]
    return read()


def get_configured_repos():
    """
    Return the set of Setuptools repository urls in our config file.
    """
    conf = read()
    if not conf:
        return []

    return [url for url in conf['SetuptoolsRepos']
            if not url.endswith(',index')]


def get_configured_index():
    """
    Return the index that is set in our config file.
    """
    conf = read()
    if not conf:
        return 'http://pypi.python.org/simple'

    # Find all of the index urls specified in the stable repos list.
    results = [url[:-6] for url in conf['SetuptoolsRepos']
               if url.endswith(',index')]

    # If there was only one index url found, then just return it.
    # If the user specified more than one index url in the config file,
    # then we print a warning.  And if no index url was found, then
    # we return None.
    if len(results) == 1:
        return results[0]

    if len(results) > 1:
        print ("Warning:  You specified more than one index URL in the "
               "config file.  Only the first one found will be used.")
        return results[0]

    return None


if __name__ == '__main__':
    write()
    print read()
