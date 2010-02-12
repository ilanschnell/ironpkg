# Copyright (c) 2008-2009 by Enthought, Inc.
# All rights reserved.

import os
import sys
from os.path import isfile, join

from enstaller import __version__
from utils import PY_VER, abs_expanduser


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


def input_userpass():
    from getpass import getpass
    print """\
Welcome to Enstaller (version %s)!

In order to access the EPD repository, please enter your
username and password, which you use to subscribe to EPD.
If you are not subscribed to EPD, hit Return.
""" % __version__
    username = raw_input('Username: ').strip()
    if not username:
        return ''
    for dummy in xrange(3):
        password = getpass('Password: ')
        password2 = getpass('Confirm passowrd: ')
        if password == password2:
            return username + ':' + password

RC_TMPL = """\
# Enstaller configuration file
# ============================
#
# This file contains the default package repositories, and configuration,
# used by Enstaller %(version)s for the Python %(py_ver)s environment:
#
#   sys.prefix = %(prefix)r
#
# This file was created by initially running the enpkg command.

%(userpass_section)s
# The enpkg command is searching for eggs in the list 'IndexedRepos'.
# When enpkg is searching for an egg, it tries to find it in the order
# of this list, and selects the first one that matches, ignoring
# repositories below.  Therefore the order of this list matters.
#
# Placeholders '{ARCH}' get substituted by 'amd64' or 'x86', depending
# on the architecture of the current interpreter.
#
# Notice also that only indexed repositories, i.e. HTTP directories which
# contain a file 'index-depend.bz2' (next to the eggs), can be listed here.
# The 'index-tool', which is also part of Enstaller may be used to create
# such repositories, see: index-tool -h
IndexedRepos = %(repos)s

# Install prefix (enpkg --prefix and --sys-prefix options overwrite this):
#prefix = '%(prefix)s'

# When running enpkg behind a firewall it might be necessary to use a proxy
# to access the repositories.  The URL for the proxy can be set here.
# Note that the enpkg --proxy option will overwrite this setting.
%(proxy_line)s

# Uncommenting the next line will disable application menu item install.
# This only effects the few packages which install menu items,
# which as IPython.
#noapp = True
"""

def write(proxy=None):
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

    if (custom_tools and hasattr(custom_tools, 'epd_baseurl') and
                         hasattr(custom_tools, 'epd_subdir')):
        epd_repo = custom_tools.epd_baseurl + custom_tools.epd_subdir + '/'
        userpass = input_userpass()
    else:
        epd_repo = None
        userpass = None

    if userpass:
        userpass_section = """
# The EPD subscriber authentication is required to access the EPD repository
# is listed below.
EPD_userpass = %r
""" % userpass
        repos = '[\n    %r,\n]' % epd_repo
    else:
        userpass_section = ""
        repos = '[]'

    py_ver = PY_VER
    prefix = sys.prefix
    version = __version__

    if proxy:
        proxy_line = 'proxy = %r' % proxy
    else:
        proxy_line = '#proxy = <proxy string>  # e.g. "123.0.1.2:8080"'

    fo = open(path, 'w')
    fo.write(RC_TMPL % locals())
    fo.close()
    print "Wrote configuration file:", path
    print 77 * '='


def get_arch():
    import platform

    if '64' in platform.architecture()[0]:
        return 'amd64'
    else:
        return 'x86'


def read():
    """
    Return the current configuration as a dictionary, and fix some values and
    give defaults.
    """
    if hasattr(read, 'cache'):
        return read.cache

    d = {}
    execfile(get_path(), d)
    read.cache = { # defaults
        'proxy': None,
        'noapp': False,
        'prefix': sys.prefix,
        'local': join(sys.prefix, 'LOCAL-REPO')
    }
    for k in ['EPD_userpass', 'IndexedRepos', 'prefix', 'proxy',
              'noapp', 'local']:
        if not d.has_key(k):
            continue
        v = d[k]
        if k == 'IndexedRepos':
            arch = get_arch()
            read.cache[k] = [url.replace('{ARCH}', arch) for url in v]
        elif k in ['prefix', 'local']:
            read.cache[k] = abs_expanduser(v)
        else:
            read.cache[k] = v

    return read()


def print_config():
    print "Python version:", PY_VER
    print "sys.prefix:", sys.prefix
    cfg_path = get_path()
    print "config file:", cfg_path
    if cfg_path is None:
        return
    conf = read()
    print
    print "config file setting:"
    for k in ['prefix', 'local', 'noapp', 'proxy']:
        print "    %s = %r" % (k, conf[k])
    print "    IndexedRepos:"
    for repo in conf['IndexedRepos']:
        print '        %r' % repo


if __name__ == '__main__':
    #write("1.2.3.4:8077")
    print_config()
