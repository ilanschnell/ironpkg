#------------------------------------------------------------------------------
# Copyright (c) 2007-2008 by Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# urllib2 handlers for proxying SSL web requests using the CONNECT method.
#------------------------------------------------------------------------------


import base64
import httplib
import socket
import urllib2

from connect_HTTP_handler import ProxyHTTPConnection


class ProxyHTTPSConnection(ProxyHTTPConnection):

    default_port = 443

    def __init__(self, host, port = None, key_file = None, cert_file = None,
        strict = None):

        ProxyHTTPConnection.__init__(self, host, port)
        self.key_file = key_file
        self.cert_file = cert_file

        return


    def connect(self):

        ProxyHTTPConnection.connect(self)

        # Make the socket ssl-aware
        ssl = socket.ssl(self.sock, self.key_file, self.cert_file)
        self.sock = httplib.FakeSocket(self.sock, ssl)

        return


class ConnectHTTPSHandler(urllib2.HTTPSHandler):

    def __init__(self, info=None, debuglevel=0):

        self.proxy_info = info
        urllib2.HTTPSHandler.__init__(self, debuglevel)

        return


    def do_open(self, http_class, req):

        if self.proxy_info is not None:
            proxy = r'%(host)s:%(port)d' % self.proxy_info
            req.set_proxy(proxy, 'https')

        # We want to have a reference to the request during the execution of
        # the connect method of our HTTPConnection.  As a result, we create an
        # instance now and then give the dp_open method a callable that returns
        # that instance rather than a class.  Isn't Python wonderful?!?
        conn = ProxyHTTPSConnection(req.host)
        conn._proxy_request = req
        conn._proxy_info = self.proxy_info
        def get_connection(host):
            conn._set_hostport(host, None)
            return conn

        return urllib2.HTTPSHandler.do_open(self, get_connection, req)

