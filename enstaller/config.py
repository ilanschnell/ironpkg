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
    for section in ['repos', 'unstable_repos']:
        cp.add_section(section)
        cp.set(section, '1', "# these should be repo URLs")

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
    if os.path.isfile(path):
        cp = ConfigParser.SafeConfigParser()
        cp.read(path)
        print 'Retrieved config from: %s' % path
    else:
        cp = init_config(path)

    return cp


def init_config(path):
    """
    Initialize the config file at the specified path.

    This will fail silently if the user can not write to the specified path.

    """

    # Save the default config to the specified file.
    cp = default_config()
    try:
        fp = open(path, 'w')
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
        if '#' != value[0]:
            results.append(value)

    # If the user wanted unstable repos, add them too.
    for name, value in cp.items('unstable_repos'):
        value = value.strip()
        if '#' != value[0]:
            results.append(value)

    return results


def _get_config_path():
    """
    Return the absolute path to our config file.

    """

    if 'win32' == sys.platform:
        name = "enstaller.ini"
    else:
        name = ".enstallerrc"

    return os.path.abspath(os.path.join(os.path.expanduser("~"), name))


