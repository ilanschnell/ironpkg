# Copyright by Enthought, Inc.
# Author: Ilan Schnell <ischnell@enthought.com>

import sys
import platform
from os.path import isfile, join

from enstaller import __version__
from utils import abs_expanduser


CONFIG_FN = ".enstaller4rc"
HOME_CONFIG_PATH = abs_expanduser("~/" + CONFIG_FN)
SYSTEM_CONFIG_PATH = join(sys.prefix, CONFIG_FN)


def get_path():
    """
    Return the absolute path to our config file.
    """
    if isfile(HOME_CONFIG_PATH):
        return HOME_CONFIG_PATH

    if isfile(SYSTEM_CONFIG_PATH):
        return SYSTEM_CONFIG_PATH

    return None


def input_auth():
    from getpass import getpass
    print """\
Welcome to Enstaller (version %s)!

In order to access the EPD repository, please enter your
username and password, which you use to subscribe to EPD.
If you are not subscribed to EPD, just hit Return.
""" % __version__
    username = raw_input('Username: ').strip()
    if not username:
        return None
    for dummy in xrange(3):
        password = getpass('Password: ')
        password2 = getpass('Confirm password: ')
        if password == password2:
            userpass = username + ':' + password
            return userpass.encode('base64').strip()
    return None

RC_TMPL = """\
# IronPkg configuration file
# ==========================
#
# This file contains the default package repositories, and configuration,
# used by IronPkg %(version)s for the IronPython environment:
#
#   sys.prefix = %(sys_prefix)r
#
# This file was created by initially running the enpkg command.

# Notice also that only indexed repositories, i.e. HTTP directories which
# contain a file 'index-depend.bz2' (next to the eggs), can be listed here.
# For local repositories, the index file is optional.  Remember that on
# Windows systems the backslaches in the directory path need to escaped, e.g.:
# r'file://C:\\repository\\' or 'file://C:\\\\repository\\\\'
IndexedRepos = [
  'http://www.enthought.com/repo/.ipy'
]
"""

def write():
    """
    Return the default state of this project's config file.
    """
    sys_prefix = sys.prefix
    version = __version__

    fo = open(HOME_CONFIG_PATH, 'w')
    fo.write(RC_TMPL % locals())
    fo.close()
    print "Wrote configuration file:", HOME_CONFIG_PATH
    print 77 * '='


def read():
    """
    Return the current configuration as a dictionary, and fix some values and
    give defaults.
    """
    if hasattr(read, 'cache'):
        return read.cache

    d = {}
    execfile(get_path(), d)
    read.cache = dict( # defaults
        info_url=None,
        prefix=sys.prefix,
        noapp=False,
        local=join(sys.prefix, 'LOCAL-REPO'),
    )
    for k in ['IndexedRepos', 'prefix', 'local']:
        if not d.has_key(k):
            continue
        v = d[k]
        if k in ['prefix', 'local']:
            read.cache[k] = abs_expanduser(v)
        else:
            read.cache[k] = v

    return read()


def print_config():
    print "Enstaller version:", __version__
    print "sys.prefix:", sys.prefix
    print "platform:", platform.platform()
    print "architecture:", platform.architecture()[0]
    cfg_path = get_path()
    print "config file:", cfg_path
    if cfg_path is None:
        return
    conf = read()
    print
    print "config file setting:"
    for k in ['info_url', 'prefix', 'local']:
        print "    %s = %r" % (k, conf[k])
    print "    IndexedRepos:"
    for repo in conf['IndexedRepos']:
        print '        %r' % repo


if __name__ == '__main__':
    write()
    print_config()
