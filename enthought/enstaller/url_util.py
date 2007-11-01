#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-05-27
#------------------------------------------------------------------------------

import re
import urllib2
from urllib import ContentTooShortError

from enthought.enstaller.text_io import \
     TextIO

# A urlretrieve function for urllib2
#   which has a reporting hook (for a progress bar)
#   Basically copied from urllib but uses urllib2.opener
def _urlretrieve(url, filename=None, reporthook=None, data=None):
    """retrieve(url) returns (filename, headers) for a local object
    or (tempfilename, headers) for a remote object."""
    fp = urllib2.urlopen(url, data)
    headers = fp.info()
    if filename:
        tfp = open(filename, 'wb')
    else:
        import tempfile
        import urllib
        garbage, path = urllib.splittype(url)
        garbage, path = urllib.splithost(path or "")
        path, garbage = urllib.splitquery(path or "")
        path, garbage = urllib.splitattr(path or "")
        suffix = os.path.splitext(path)[1]
        (fd, filename) = tempfile.mkstemp(suffix)
        tfp = os.fdopen(fd, 'wb')
    result = filename, headers
    bs = 1024*8
    size = -1
    read = 0
    blocknum = 0
    if reporthook:
        if "content-length" in headers:
            size = int(headers["Content-Length"])
        reporthook(blocknum, bs, size)
    while 1:
        block = fp.read(bs)
        if block == "":
            break
        read += len(block)
        tfp.write(block)
        blocknum += 1
        if reporthook:
            reporthook(blocknum, bs, size)
    fp.close()
    tfp.close()
    del fp
    del tfp

    # raise exception if actual size does not match content-length header
    if size >= 0 and read < size:
        raise ContentTooShortError("retrieval incomplete: got only %i out "
                                   "of %i bytes" % (read, size), result)

    return result
  
    

class URLUtil( TextIO ) :
    """
    Class to gracefully handle timeouts, etc. for urllib functions.
    """

    retries_on_timeout = 2

    retry_msg = "Timed out accessing %s...retrying.\n"
    
    bad_url_warning = "Warning: URL %s could not be opened.\n" + \
                      "The error was: %s\n" + \
                      "This URL will not be used.\n"

    too_many_retries = "Operation timed out %s times while trying to " + \
                       "access URL %s.\nThis URL will not be used.\n"
    
    successful_read_msg = "Successfully read %s\n"

    #
    # Set to True if the wrapper is to re-raise bad URL exceptions instead of
    # logging them (will still retry on timeouts)
    #
    reraise_on_bad_urls = False
    
    
    def urlopen(self, url):
        """
        Calls urllib.urlopen() on the URL, handling bad URLs and timeouts.
        """
        #
        # urllib.urlopen does not accept file:// (???)
        #    but urllib2 does
        #if( re.match( "^file://", url, re.IGNORECASE ) ) :
        #    url = url[7:]
            
        return self._urllib_wrapper(urllib2.urlopen, url)

    def urlretrieve(self, url, dest=None, reporthook=None):
        """
        Calls equivalent of urllib.urlretrieve() on the URL, 
            handling bad URLs and timeouts.
        """
        return self._urllib_wrapper(_urlretrieve, url, dest, reporthook)
    

    def _urllib_wrapper(self, func, url, *args) :
        """
        Calls urllib functions which take a url as the first arg, handling
        errors gracefully and retries on timeouts.
        """
        retval = None
        retries = 0
        err = ""
        
        while (retries < self.retries_on_timeout):
            try :
                retval = apply(func, ((url,) + args))
                #
                # Print a confirmation if the URL had to be retried.
                #
                if(retries > 0):
                    self.log(self.successful_read_msg % url)
                break
            
            except IOError, err :
                #
                # Check for timeout, all other socket errs are bad URLs
                #
                socket_err = ""
                if len(err.args) > 1 and err.args[0] == "socket error":
                    socket_err = err.args[1].args[1]

                if (socket_err == "Operation timed out"):
                    self.log(self.retry_msg % url)
                    retries += 1
                    continue

                if (self.reraise_on_bad_urls):
                    raise
                else :
                    self.log(self.bad_url_warning % (url, err))
                    break
        #
        # Print a message if the max retries has been exceeded.
        #
        if (retries >= self.retries_on_timeout):
            self.log(self.too_many_retries % (url, self.retries_on_timeout+1))
            
        return retval
