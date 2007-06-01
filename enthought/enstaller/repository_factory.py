#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2006-08-10
#------------------------------------------------------------------------------

import socket
import xmlrpclib

from enstaller.run_enstaller import IS_WINDOWS
from enstaller.local_repository import LocalRepository
from enstaller.remote_repository import RemoteRepository
from enstaller.pypi_repository import PypiRepository


def create_repository( url, verbose, prompting, logging_handle ) :
    """
    Given a URL, returns an instance of the appropriate Repository object type.
    """
    repo = None
    
    remote = [url.lower().startswith( p ) for p in ["http:", "https:"]]
    if( True in remote ) :
        #
        # check if it is a pypi-style repo by trying to access it via an
        # XMLRPC call...set the server var as well
        #
        xmlrpc_server = xmlrpclib.Server( url )

        try :
            xmlrpc_server.package_releases( "" )
            repo = PypiRepository( location=url,
                                   verbose=verbose,
                                   prompting=prompting,
                                   logging_handle=logging_handle )
            repo.xmlrpc_server = xmlrpc_server

        except socket.gaierror, err :
            repo = None

        except xmlrpclib.ProtocolError :
            repo = RemoteRepository( location=url,
                                     verbose=verbose,
                                     prompting=prompting,
                                     logging_handle=logging_handle )
    else :
        #
        # If the URL has a file:// protocol, remove it to make the URL a
        # valid local directory name.  If on Windows, make sure extra / are
        # not left before the start of a path.
        #
        if( url.lower().startswith( "file://" ) ) :
            url = url[7:]
            if( IS_WINDOWS ) :
                url = url.strip( "/" )
                    
        repo = LocalRepository( location=url,
                                verbose=verbose,
                                prompting=prompting,
                                logging_handle=logging_handle )
                                
    return repo

