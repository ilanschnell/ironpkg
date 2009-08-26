# Copyright (c) 2008-2009 by Enthought, Inc.
# All rights reserved.

import os
import stat
import sys

from distutils.sysconfig import get_python_lib
from os.path import abspath, expanduser, isfile, join

from enstaller import __version__


CONFIG_NAME = ".enstaller4rc"
HOME_CONFIG_PATH = abspath(expanduser("~/" + CONFIG_NAME))
SYSTEM_CONFIG_PATH = abspath(join(get_python_lib(), CONFIG_NAME))


def get_path():
    """
    Return the absolute path to our config file.
    """
    if isfile(HOME_CONFIG_PATH):
        return HOME_CONFIG_PATH

    if isfile(SYSTEM_CONFIG_PATH):
        return SYSTEM_CONFIG_PATH

    return None


def write_default():
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
    else:
        epd_repo = None

    enst_ver = __version__
    if epd_repo:
        print """\
Welcone Enstaller (version %(enst_ver)s)!

Please enter your OpenID which you use to subscribe to EPD.
The repository for your install of EPD is located:
%(epd_repo)s

Your OpenID and the location of the EPD repository will be stored in the
Enstaller configuration file
%(path)s
which you may change at any point by editing the file.
See the configuration file for more details.

If you are not subscribed to EPD, just hit Return.
""" % locals()
        openid = raw_input('OpenID: ').strip()
        repos = '[\n    %r,\n]' % epd_repo
    else:
        openid = ''
        repos = '[]'

    py_ver = sys.version[:3]
    prefix = sys.prefix

    fo = open(path, 'w')
    fo.write("""\
# Enstaller configuration file
# ============================
#
# This file contains the default package repositories used by
# Enstaller-%(enst_ver)s for Python %(py_ver)s installed in:
#
#     %(prefix)s
#
# This file created by initially running the enpkg command.

# EPD subscriber OpenID:
EPD_OpenID = %(openid)r


# This list of repositories may include the EPD repository.  However,
# if the EPD repository is listed here things will only work if the
# correct EPD subscriber OpenID is provided above.
IndexedRepos = %(repos)s


# Setuptools (easy_install) repositories, the index url is specified by
# appending a ',index' to the end of a URL.  There can only be one index
# listed here and when this file is created by default the index is set to
# the PyPI index.
SetuptoolsRepos = [
    'http://pypi.python.org/simple,index',  # Python Package Index
]
""" % locals())
    fo.close()


def parse():
    """
    Return the current configuration.
    """
    pass


def get_configured_repos(verbose=False):
    """
    Return the set of repository urls in our config file.

    The config file allows for a declaration of unstable repos as well, but
    these are only included in the returned set if the 'unstable' argument is
    true.

    """
    results = []

    # Add all the stable repos to the results list in the sorted order
    # of their keys.
    cp = get_config(verbose=verbose)
    for name, value in sorted(cp.items('repos')):
        value = value.strip()
        if not value.startswith('#') and not value.endswith(',index'):
            results.append(value)

    return results


def get_configured_index(verbose=True):
    """
    Return the index that is set in our config file.

    """
    # Find all of the index urls specified in the stable repos list.
    results = []
    cp = get_config()
    for name, value in sorted(cp.items('repos')):
        value = value.strip()
        if value.endswith(',index'):
            results.append(value[:-6])

    # If there was only one index url found, then just return it.
    # If the user specified more than one index url in the config file,
    # then we print a warning.  And if no index url was found, then
    # we return None.
    if len(results) == 1:
        return results[0]
    elif len(results) > 1:
        if verbose:
            print ("Warning:  You specified more than one index URL in the "
                "config file.  Only the first one found will be used.")
        return results[0]
    else:
        # FIXME:  For now we just return 'dummy' if no index URL is specified,
        # but eventually we would like to modify the setuptools code base to
        # not have to use an index URL.
        return None


if __name__ == '__main__':
    write_default()
