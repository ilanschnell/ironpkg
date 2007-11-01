#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Travis Oliphant 2007-10-30
#------------------------------------------------------------------------------

import os
import urllib2

def install_proxy_handler(proxy_dict):
    """Use a proxy for future urllib2.urlopen commands
    """
    if proxy_dict['host'] is None:
        # install default handler
        urllib2.install_opener(None)

    if proxy_dict['user'] is None or proxy_dict['pass'] is None:
        # No authentication
        httpstr = 'http://%(host)s:%(port)d' % proxy_dict
    else:
        # Authentication
        httpstr = 'http://%(user)s:%(pass)s@%(host)s:%(port)d' % proxy_dict
    
    proxy_support = urllib2.ProxyHandler({"http" : httpstr})
    opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
    
    urllib2.install_opener(opener)

# command-line string is in proxystr
#  it over-rides whatever is in environment variables.    
def check_and_install_proxy(proxystr):
    if proxystr == '':
        proxy_info = {
            'host' : os.environ.get('PROXY_HOST', None)
            'port' : os.environ.get('PROXY_PORT', 80)
            'user' : os.environ.get('PROXY_USER', None)
            'pass' : os.environ.get('PROXY_PASS', None)
            }
    else: # get it from the string
        errmsg = "Invalid proxy string"
        proxy_info = {}
        res = proxystr.split('@')
        if len(res) == 1:
            user_pass = [None]
            host_port = res[0].split(':')
        elif len(res) == 2:
            user_pass = res[0].split(':')
            host_port = res[1].split(':')
        else:
            raise ValueError, errmsg

        if len(user_pass) == 1:
            proxy_info['user'] = user_pass[0]
            proxy_info['pass'] = None
        elif len(user_pass) == 2:
            proxy_info['user'] = user_pass[0]
            proxy_info['pass'] = user_pass[1]
        else:
            raise ValueError, errmsg
        
        if len(host_port) == 1:
            proxy_info['host'] = host_port[0]
            proxy_info['port'] = 80
        elif len(host_port) == 2:
            proxy_info['host'] = host_port[0]
            proxy_info['port'] = host_port[1]
        else:
            raise ValueError, errmsg
        
    install_proxy_handler(proxy_info)
    return proxy_info
    
