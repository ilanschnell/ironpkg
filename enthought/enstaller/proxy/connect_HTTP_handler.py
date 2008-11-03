#------------------------------------------------------------------------------
# Copyright (c) 2007 by Enthought, Inc.
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
import urllib
import urllib2


class ProxyHTTPConnection(httplib.HTTPConnection):

    _ports = {'http':80, 'https':443}


    def connect(self):
        """
        Open the network connection for the request.

        Overridden to setup a tunnel for the request through the proxy via a
        CONNECT request and response.  This follows the description of RFC2817
        as described here: ftp://ftp.isi.edu/in-notes/rfc2817.txt

        """

        # Initiate the actual network connection.
        httplib.HTTPConnection.connect(self)

        # Send the CONNECT message to the proxy.
        msg = self._build_connect_message()
        self.send(msg)

        # Read the proxy's response.  Note that closing the response does NOT
        # close the socket.
        response = self.response_class(self.sock, strict=self.strict,
            method=self._method, debuglevel=self.debuglevel)
        version, status, reason = response._read_status()
        while True:
            line = response.fp.readline()
            if self.debuglevel > 0:
                print "reply:", repr(line)
            if line == '\n' or line == '\r\n':
                break
        response.close()

        # If we can't communicate with the proxy, we have to completely punt
        # on the request.
        if status != 200:
            self.close()
            raise socket.error("Proxy failure: %d %s" % (status, reason))

        return


    def _build_connect_message(self):
        """
        Return a CONNECT message to be sent to the proxy.

        """

        # Retrieve the real target host and port we want to contact.
        authority = self._get_real_authority()

        # We always need the following headers.
        headers = {
            'Proxy-Connection': 'keep-alive',
            'Host': authority,
            'User-Agent': 'Python/2.5',
            }

        # If we have credentials to authenticate to the proxy, then proactively
        # provide the appropriate header.
        if self._proxy_info['pass'] is not None:
            raw = "%(user)s:%(pass)s" % self._proxy_info
            auth = 'Basic %s' % base64.encodestring(raw).strip()
            headers['Proxy-Authorization'] = auth

        # Assemble the message content to be sent
        buffer = ['CONNECT %s HTTP/1.0' % authority]
        for k, v in headers.items():
            buffer.append('%s: %s' % (k, v))
        buffer.extend(("", ""))
        msg = "\r\n".join(buffer)

        return msg


    def _get_real_authority(self):
        """
        Return the authority specification of the originally requested URL.

        The return value is a string of the form <host>:<port>.

        """

        url = self._proxy_request.get_selector()

        proto, rest = urllib.splittype(url)
        if proto is None:
            raise ValueError("unknown URL type: %s" % url)

        # Get the host and port specification
        host, rest = urllib.splithost(rest)
        host, port = urllib.splitport(host)

        # If port is not defined, then try to get it from the protocol.
        if port is None:
            try:
                port = self._ports[proto]
            except KeyError:
                raise ValueError("unknown protocol for: %s" % url)

        return '%s:%d' % (host, port)


class ConnectHTTPHandler(urllib2.HTTPHandler):

    def __init__(self, info=None, debuglevel=0):

        self.proxy_info = info
        urllib2.HTTPHandler.__init__(self, debuglevel)

        return


    def do_open(self, http_class, req):

        if self.proxy_info is not None:
            proxy = r'%(host)s:%(port)d' % self.proxy_info
            req.set_proxy(proxy, 'http')

        # We want to have a reference to the request during the execution of
        # the connect method of our HTTPConnection.  As a result, we create an
        # instance now and then give the dp_open method a callable that returns
        # that instance rather than a class.  Isn't Python wonderful?!?
        conn = ProxyHTTPConnection(req.host)
        conn._proxy_request = req
        conn._proxy_info = self.proxy_info
        def get_connection(host):
            conn._set_hostport(host, None)
            return conn

        return urllib2.HTTPHandler.do_open(self, get_connection, req)

