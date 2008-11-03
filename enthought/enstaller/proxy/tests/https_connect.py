#------------------------------------------------------------------------------
# Copyright (c) 2007 by Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#------------------------------------------------------------------------------


import urllib2

from enthought.proxy.api import ConnectHTTPHandler, ConnectHTTPSHandler


if __name__ == '__main__':

    import sys

    # Point this at a working proxy server.  The below is specific to my
    # machine.
    p_info = {'host':'10.1.10.187', 'port':3128, 'user':'user', 'pass':'user'}

    # Setup urllib2 to connect through the proxy for http and https.
    opener = urllib2.build_opener(
        ConnectHTTPHandler(info=p_info),
        ConnectHTTPSHandler(info=p_info),
        )
    urllib2.install_opener(opener)

    # Try an HTTPS request
    f = urllib2.urlopen(r"https://svn.enthought.com/svn/enthought")
    print f.read()
    f.close()
    print "\n\n"

    # Try an HTTP request
    f = urllib2.urlopen(r"http://code.enthought.com/enstaller/eggs")
    print f.read()
    f.close()
    print "\n\n"

