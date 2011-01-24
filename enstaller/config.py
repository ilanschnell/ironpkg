# Copyright by Enthought, Inc.
# Author: Ilan Schnell <ischnell@enthought.com>

import re
import os
import sys
import platform
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
# Enstaller configuration file
# ============================
#
# This file contains the default package repositories, and configuration,
# used by Enstaller %(version)s for the Python %(py_ver)s environment:
#
#   sys.prefix = %(sys_prefix)r
#
# This file was created by initially running the enpkg command.

%(auth_section)s
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
# For local repositories, the index file is optional.  Remember that on
# Windows systems the backslaches in the directory path need to escaped, e.g.:
# r'file://C:\\repository\\' or 'file://C:\\\\repository\\\\'
IndexedRepos = [
%(repo_section)s]

# The following variable is optional and, if provided, point to a URL which
# contains an index file with additional package information, such as the
# package home-page, license type, description.  The information is displayed
# by the --info option.
%(comment_info)sinfo_url = 'http://www.enthought.com/epd/index-info.bz2'

# Install prefix (enpkg --prefix and --sys-prefix options overwrite this).
# When this variable is not provided, it will default to the value of
# sys.prefix (within the current interpreter running enpkg)
#prefix = %(sys_prefix)r

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

    if (custom_tools and hasattr(custom_tools, 'repo_section')):
        auth = input_auth()
    else:
        auth = None

    if auth:
        auth_section = """
# The EPD subscriber authentication is required to access the EPD repository.
# To change this setting, use the 'enpkg --userpass' command which will ask
# you for your username and password.
EPD_auth = %r
""" % auth
        repo_section = custom_tools.repo_section
        comment_info = ''
    else:
        auth_section = ''
        repo_section = ''
        comment_info = '#'

    py_ver = PY_VER
    sys_prefix = sys.prefix
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


def change_auth():
    path = get_path()
    if path is None:
        print "The enstaller configuration file '.enstaller4rc' was not found."
        sys.exit(1)
    f = open(path, 'r+')
    data = f.read()
    auth = input_auth()
    if auth:
        pat = re.compile(r'^EPD_auth\s*=.*$', re.M)
        authline = 'EPD_auth = %r' % auth
        if pat.search(data):
            data = pat.sub(authline, data)
        else:
            lines = data.splitlines()
            lines.insert(10, authline)
            data = '\n'.join(lines)
        f.seek(0)
        f.write(data)
    f.close()


def get_arch():
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
    read.cache = dict( # defaults
        info_url=None,
        prefix=sys.prefix,
        proxy=None,
        noapp=False,
        local=join(sys.prefix, 'LOCAL-REPO'),
    )
    for k in ['EPD_auth', 'EPD_userpass', 'IndexedRepos', 'info_url',
              'prefix', 'proxy', 'noapp', 'local']:
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
    for k in ['info_url', 'prefix', 'local', 'noapp', 'proxy']:
        print "    %s = %r" % (k, conf[k])
    print "    IndexedRepos:"
    for repo in conf['IndexedRepos']:
        print '        %r' % repo


if __name__ == '__main__':
    #write("1.2.3.4:8077")
    write()
    print_config()
