#------------------------------------------------------------------------------
# Copyright (c) 2007 by Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
#------------------------------------------------------------------------------


import os
import urllib2

from connect_HTTP_handler import ConnectHTTPHandler
from connect_HTTPS_handler import ConnectHTTPSHandler


def install_proxy_handlers(pinfo):
    """
    Use a proxy for future urllib2.urlopen commands.

    The specified pinfo should be a dictionary containing the following:
        * host: the servername of the proxy
        * port: the port to use on the proxy server
        * user: (optional) username for authenticating with the proxy server.
        * pass: (optional) password for authenticating with the proxy server.

    """

    h = pinfo['host']
    p = pinfo['port']
    usr = pinfo['user']
    pwd = pinfo['pass']

    # Only install a custom opener if a host was actually specified.
    if h is not None and len(h) > 0:
        handlers = []

        # Add handlers to deal with using the proxy.
        handlers.append(ConnectHTTPSHandler(info=pinfo))
        handlers.append(ConnectHTTPHandler(info=pinfo))

        # Create a proxy opener and install it.
        opener = urllib2.build_opener(*handlers)
        urllib2.install_opener(opener)

    return


def get_proxy_info(proxystr=None):
    """
    Get proxy config from string or environment variables.

    If a proxy string is passed in, it overrides whatever might be in the
    environment variables.

    Returns dictionary of identified proxy information.

    Raises ValueError on any configuration error.

    """

    default_port = 80

    # Only check for env variables if no explicit proxy string was provided.
    if proxystr is None or len(proxystr) < 1:
        proxy_info = {
            'host' : os.environ.get('PROXY_HOST', None),
            'port' : os.environ.get('PROXY_PORT', default_port),
            'user' : os.environ.get('PROXY_USER', None),
            'pass' : os.environ.get('PROXY_PASS', None)
            }

    # Parse the passed proxy string
    else:
        proxy_info = {}
        res = proxystr.split('@')
        if len(res) == 1:
            user_pass = [None]
            host_port = res[0].split(':')
        elif len(res) == 2:
            user_pass = res[0].split(':')
            host_port = res[1].split(':')
        else:
            raise ValueError('Invalid proxy string: "%s"' % proxystr)

        if len(user_pass) == 1:
            proxy_info['user'] = user_pass[0]
            proxy_info['pass'] = None
        elif len(user_pass) == 2:
            proxy_info['user'] = user_pass[0]
            proxy_info['pass'] = user_pass[1]
        else:
            raise ValueError('Invalid user:pass in proxy string: '
                '"%s"' % user_pass)

        if len(host_port) == 1:
            proxy_info['host'] = host_port[0]
            proxy_info['port'] = default_port
        elif len(host_port) == 2:
            proxy_info['host'] = host_port[0]
            try:
                p = int(host_port[1])
            except:
                raise ValueError('Port specification must be an integer.  '
                    'Had "%s"' % host_port[1])
            proxy_info['port'] = p
        else:
            raise ValueError('Invalid host:port in proxy string: '
                '"%s"' % host_port)

    # If a user was specified, but no password was, prompt for it now.
    user = proxy_info.get('user', None)
    if user is not None and len(user) > 0:
        pwd = proxy_info.get('pass', None)
        if pwd is None or len(pwd) < 1:
            import getpass
            proxy_info['pass'] = getpass.getpass()

    return proxy_info


def setup_authentication(cfg, opener=None):
    """
    """

    # Configure a password manager with the user's authentication info.
    passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    section = 'url auth info'
    if cfg.has_section(section):
        for dummy, info in cfg.items(section):

            # Ensure the info includes both a username and a url.
            if '@' not in info:
                raise ValueError('Invalid %s string: "%s"' % (section, info))
            userpass, url = info.split('@')

            # Ensure we have both a user and password.
            if ':' in userpass:
                user, password = userpass.split(':')
            else:
                user = userpass
                prompt = 'Password for %s@%s: ' % (user, url)
                import getpass
                password = getpass.getpass(prompt)

            passmgr.add_password(None, url, user, password)

    # Create a basic auth handler that uses our authentication info.
    handler = urllib2.HTTPBasicAuthHandler(passmgr)

    # Add to an existing opener if one was specified and otherwise, create and
    # register our own.
    if opener is not None:
        opener.add_handler(handler)
    else:
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

    return


def setup_proxy(proxystr=''):
    """
    Configure and install proxy support.

    The specified proxy string is parsed via ``get_proxy_info`` and then
    installed via ``install_proxy_handler``.  If proxy settings are detected
    and a handler is installed, then this method returns True.  Otherwise it
    returns False.

    Raises ValueError in the event of any problems.

    """

    installed = False

    info = get_proxy_info(proxystr)
    if 'host' in info and info['host'] is not None:
        install_proxy_handlers(info)
        installed = True

    return installed
