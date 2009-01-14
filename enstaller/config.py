#------------------------------------------------------------------------------
# Copyright (c) 2008, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Dave Peterson
#------------------------------------------------------------------------------


import ConfigParser
from distutils import sysconfig
import os
import stat
import sys


def default_config():
    """
    Return the default state of this project's config file.

    We expect the config to consist of the following sections:

    "repos": This is a list of "key = value" type pairs where the keys must
        simply be unique values, and the values are URLs to distribution
        repositories.  These repositories are expected to contain released, or
        widely available, distributions.

    "unstable_repos": This is a list of "key = value" type pairs where the keys
        must simply be unique values, and the values are URLs to distribution
        repositories.  These repositories are expected to contain development
        distributions only. i.e. "unstable" distributions.

    """

    cp = ConfigParser.SafeConfigParser()
    
    # By default, set the index url to the pypi index in the 'repos' section.
    cp.add_section('repos')
    cp.set('repos', '1', "http://pypi.python.org/simple,index")
    
    # Also set the 'unstable_repos' section to its previous default.
    cp.add_section('unstable_repos')
    cp.set('unstable_repos', '1', "# these should be repo URLs")

    return cp


def get_config():
    """
    Return the current configuration.

    """

    # Try to read the current config.  If the config file doesn't exist,
    # just create a new config file with our default config.   We do this to
    # try and give user's a template to fill out rather than having to guess at
    # the format of our config file.
    path = _get_config_path()
    if path:
        cp = ConfigParser.SafeConfigParser()
        cp.read(path)
        print 'Retrieved config from: %s' % path
    else:
        path = _get_default_config_path()
        cp = init_config(path)

    return cp


def init_config(path):
    """
    Initialize the config file at the specified path.

    This will fail silently if the user can not write to the specified path.

    """
    from enstaller import __version__

    DATA = dict(py_ver=sys.version[:3],
                prefix=sys.prefix,
                enst_ver=__version__)

    # Save the default config to the specified file.
    cp = default_config()
    try:
        fp = open(path, 'w')
        fp.write("""\
# This file contains the default package repositories used by
# Enstaller version %(enst_ver)s for Python %(py_ver)s installed at
#
#     %(prefix)s
#
# The index url is specified by appending a ',index' to the end of a URL.
# There can only be one index listed here and when this file is created
# by default the index is set to the PyPI index.\n
""" % DATA)
        cp.write(fp)
        fp.close()
        os.chmod(path, stat.S_IRUSR|stat.S_IWUSR)
        print 'Created config file: %s' % path
    except IOError:
        pass

    return cp


def get_configured_repos(unstable=False):
    """
    Return the set of repository urls in our config file.

    The config file allows for a declaration of unstable repos as well, but
    these are only included in the returned set if the 'unstable' argument is
    true.

    """

    results = []

    # Add all the stable repos to the results list.
    cp = get_config()
    for name, value in cp.items('repos'):
        value = value.strip()
        if not value.startswith('#') and not value.endswith(',index'):
            results.append(value)

    # If the user wanted unstable repos, add them too.
    if unstable:
        for name, value in cp.items('unstable_repos'):
            value = value.strip()
            if not value.startswith('#') and not value.endswith(',index'):
                results.append(value)

    return results
    

def get_configured_index():
    """
    Return the index that is set in our config file.
    """
    
    # Find all of the index urls specified in the stable repos list.
    results = []
    cp = get_config()
    for name, value in cp.items('repos'):
        value = value.strip()
        if value.endswith(',index'):
            results.append(value[:-6])
    
    # If there was only one index url found, then just return it.
    # If the user specified more than one index url in the config file,
    # then we print a warning.  And if no index url was found, then
    # just return 'dummy'.
    if len(results) == 1:
        return results[0]
    elif len(results) > 1:
        print ("Warning:  You specified more than one index URL in the config "
            "file.  Only the first one found will be used.")
        return results[0]
    else:
        # FIXME:  For now we just return 'dummy' if no index URL is specified, but eventually
        # we would like to modify the setuptools code base to not have to use an index URL.
        return 'dummy'


def _get_default_config_path():
    """
    Return the path to the default config file in a user's HOME directory.
    """
    
    if sys.platform == 'win32':
        name = "enstaller.ini"
    else:
        name = ".enstallerrc"
    return os.path.abspath(os.path.join(os.path.expanduser("~"), name))
    
    
def _get_config_path():
    """
    Return the absolute path to our config file.

    """

    # First, look for the config file in the user's HOME directory.
    # If the config file can be found here, then return its path.
    file_path = _get_default_config_path()
    if os.path.exists(file_path):
        return file_path
        
    # If a config file can't be found in the user's HOME directory,
    # then look for one in the system site-packages.  Also, the name of
    # the config file in site-packages is different on non-Windows platforms
    # so that it will sort next to the Enstaller egg.
    if sys.platform == 'win32':
        name = "enstaller.ini"
    else:
        name = "enstaller.rc"
    site_packages = sysconfig.get_python_lib()
    file_path = os.path.abspath(os.path.join(site_packages, name))
    if os.path.exists(file_path):
        return file_path
    
    # If we reach this point, it means that we couldn't locate a config
    # file in the user's HOME directory or the system site-packages,
    # so just return None.
    return None

