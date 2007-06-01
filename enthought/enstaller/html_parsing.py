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

#
# This module contains several small classes used for parsing html associated
# with Python package repositories (mainly egg repositories for now).
#

import string
import re
from os import path
import sys
import formatter
import htmllib

from threading import \
     Thread

from enstaller.run_enstaller import \
     TextIO, URLUtil
from enstaller.package import \
     is_egg_installable



class EggHTMLFormatter( formatter.NullFormatter ) :
    """
    Used for generating output or making other calls.
    """
    pass



class EggHTMLDirListingParser( htmllib.HTMLParser, TextIO ) :
    """
    class which parses the directory listing html from a web server
    and extracts the egg names which are available
    """

    def __init__( self, url, formatter, only_find_installable=False, **kwargs ) :
        """
        If only_find_installable is set, return only eggs that are installable on
        the machine running the code
        """
        htmllib.HTMLParser.__init__( self, formatter )
        TextIO.__init__( self, **kwargs )
        
        self.formatter = formatter
        if( url.endswith( "/" ) ) :
            self.url = url[:-1]
        else :
            self.url = url
        self.egg_patt = re.compile( ".*\.egg$" )
        self.egg_info_patt = re.compile( ".*\.egg.info$" )

        self.only_find_installable = only_find_installable
        
        #
        # dictionary mapping egg name to another dictionary of info
        #
        self.eggs_info_dict = {}

        #
        # URLUtil used for accessing URLs with error handling
        # (takes same args as TextIO)
        #
        self._urlutil = URLUtil( **kwargs )
        

    def start_a( self, attrs ) :
        """
        adds the URL encountered by the <a...> tag if it matches what is
        believed to be an egg URL.  If self.only_find_installable is set, add it
        only if it is an egg which is believed to be installable on the current
        machine.
        """
        if( len( attrs ) > 0 ) :
            for attr in attrs :
                if( attr[0] == "href" ) :
                    #
                    # found an egg URL
                    #
                    if( self.egg_patt.match( attr[1] ) ) :
                        url = self._fixup_url( attr[1] )
                        egg_name = path.basename( url )

                        if( self.only_find_installable ) :
                            if( is_egg_installable( egg_name ) ) :
                                self.debug( "Found: %s\n" % url )
                                self._add_info( egg_name, "download_url", url )
                            else :
                                pass
                                self.debug( "Skipping non-installable : %s\n" \
                                            % url )
                        else :
                            self.debug( "Found: %s\n" % url )
                            self._add_info( egg_name, "download_url", url )
                    #
                    # found an egg.info URL
                    #
                    elif( self.egg_info_patt.match( attr[1] ) ) :
                        url = self._fixup_url( attr[1] )
                        egg_name = path.basename( url )[0:-5]

                        if( self.only_find_installable ) :
                            if( is_egg_installable( egg_name ) ) :
                                self.debug( "Found: %s\n" % url )
                                self._add_info( egg_name, "info_url", url )
                            else :
                                pass
                                self.debug( "Skipping non-installable : %s\n" \
                                            % url )
                        else :
                            self.debug( "Found: %s\n" % url )
                            self._add_info( egg_name, "info_url", url )


    #############################################################################
    # Protected interface.
    #############################################################################

    def _fixup_url( self, url ) :
        """
        fixup the url to assure it is abs path / accessible
        """
        if( not( path.exists( url ) ) and \
            not( url.startswith( "http" ) ) ) :
            url = path.join( self.url, url ).replace( "\\", "/" )
        return url


    def _add_info( self, egg_name, key, val ) :
        """
        adds the key, value pair to the dictionary of eggs info
        """
        if( self.eggs_info_dict.has_key( egg_name ) ) :
            self.eggs_info_dict[egg_name][key] = val
        else :
            self.eggs_info_dict[egg_name] = {key : val}
            

    def get_egg_info( self ) :
        """
        returns a list of tuples of (egg_name, egg_info_dictionary), and the
        dictionary can contain a download_url and/or an info_url (link to an
        egg .info file containing meta-data)
        """
        return self.eggs_info_dict.items()



###############################################################################
## START of classes for finding eggs on a pypi-style repository without using
## XMLRPC calls
###############################################################################

class EggHTMLPyPIParser( EggHTMLDirListingParser ) :
    """
    Extends EggHTMLDirListingParser for use with a PyPI site.

    Parses a PyPI-style html doc and extracts the egg names which are
    available...all meta-data is assumed to be retrievable from XMLRPC calls
    later.

    Make several assumptions here: initial html is a dir listing of py versions
    which contain packages for that version, as well as any and source.  From
    those links, there is another dir listing of single characters which
    contin packages starting with that letter, then finally a dir listing with
    each package which when followed will show the actual package.

    For example:
    http://cheeseshop.python.org/packages/2.4/A/Aglyph/Aglyph-0.8-py2.4.egg
    """

    def __init__( self, url, formatter, **kwargs ) :
        """
        Construct 
        """
        EggHTMLDirListingParser.__init__( self, url, formatter, **kwargs )
        self.py_version = "%s.%s" % (sys.version_info[0], sys.version_info[1])
        

    def start_a( self, attrs ) :
        """
        This starts on the py_version page, for example:
        http://cheeseshop.python.org/packages/2.4
        and makes recursive calls from there to do a depth-first search for
        all packages.
        """
        if( len( attrs ) > 0 ) :
            for attr in attrs :
                if( attr[0] == "href" ) :

                    if( attr[1].endswith( "/" ) ) :
                        link = attr[1][:-1]
                    else :
                        link = attr[1]
                        
                    if( link in [self.py_version, "any"] ) :

                        newlink = "%s/%s" % (self.url, link)

                        parser = EggHTMLPyPIPackageLetterParser(
                            newlink,
                            self.formatter,
                            logging_handle=self.logging_handle,
                            verbose=self.verbose,
                            prompting=self.prompting )


                        url_handle = self._urlutil.urlopen( newlink )
                        if( not( url_handle is None ) ) :
                            response = url_handle.read()

                            parser.feed( response )
                            parser.sync()
                            self.eggs_info_dict.update( parser.get_egg_info() )



class EggHTMLPyPIPackageLetterParser( EggHTMLDirListingParser ) :
    """
    Instantiated from a EggHTMLPyPIParser() class for following all the
    package letter links in a url of this style:
    http://cheeseshop.python.org/packages/2.4/A/Aglyph/Aglyph-0.8-py2.4.egg
    In the example above, all subdirs of "2.4" would be traversed
    (A, B, C, etc.) and separate EggHTMLPyPIPackageListParsers would be
    instantiated.
    """
    def __init__( self, url, formatter, **kwargs ) :
        
        EggHTMLDirListingParser.__init__( self, url, formatter, **kwargs )
        self.valid_links = [x for x in string.ascii_letters + string.digits]
        self.parsers = []
        self.threads_running = 0
        self.max_threads = 30

        
    def start_a( self, attrs ) :
        """
        This starts on the package letter page, for example:
        http://cheeseshop.python.org/packages/2.4/A
        and makes recursive calls from there to do a depth-first search for
        all packages.
        """
        if( len( attrs ) > 0 ) :
            for attr in attrs :
                if( attr[0] == "href" ) :

                    if( attr[1].endswith( "/" ) ) :
                        link = attr[1][:-1]
                    else :
                        link = attr[1]

                    if( link in self.valid_links ) :

                        newlink = "%s/%s" % (self.url, link)
                        self.log( "  reading %s\n" % newlink )

                        parser = EggHTMLPyPIPackageListParser(
                            newlink,
                            self.formatter,
                            logging_handle=self.logging_handle,
                            verbose=self.verbose,
                            prompting=self.prompting )
                        
                        self.parsers.append( parser )
                        parser.start()
                        self.threads_running += 1

                        if( self.threads_running >= self.max_threads ) :
                            self.sync()


    def sync( self ) :
        """
        Iterates over all the outstanding threads and calls join() on them,
        which causes them to "join" with the main thread (I think).  After that,
        their results can be combined and the thread count and list can be
        reset.
        """
        for parser in self.parsers :
            parser.join()
            self.eggs_info_dict.update( parser.get_egg_info() )

        self.parsers = []
        self.threads_running = 0
            


class EggHTMLPyPIPackageListParser( EggHTMLDirListingParser, Thread ) :
    """
    Instantiated from a EggHTMLPyPIPackageLetterParser() class for following
    all the package name links in a url of this style:
    http://cheeseshop.python.org/packages/2.4/A/Aglyph/Aglyph-0.8-py2.4.egg
    In the example above, all subdirs of "A" would be traversed
    (Aglyph, Amara, etc.) and separate EggHTMLDirListingParsers would be
    instantiated.
    """
    def __init__( self, url, formatter, **kwargs ) :
        Thread.__init__( self )
        EggHTMLDirListingParser.__init__( self, url, formatter, **kwargs )
        self.parent_dir_url = path.dirname( self.url )

    def run( self ) :
        url_handle = self._urlutil.urlopen( self.url )

        if( not( url_handle is None ) ) :
            response = url_handle.read()
            self.feed( response )
            self.eggs_info_dict.update( self.get_egg_info() )
        

    def start_a( self, attrs ) :
        """
        This starts on the package letter page, for example:
        http://cheeseshop.python.org/packages/2.4/A
        and makes recursive calls from there to do a depth-first search for
        all packages.
        """
        if( len( attrs ) > 0 ) :
            for attr in attrs :

                if( attr[0] == "href" ) :

                    if( attr[1].endswith( "/" ) ) :
                        link = attr[1][:-1]
                    else :
                        link = attr[1]

                    #
                    # dont traverse the "parent dir" link
                    #
                    if( self.parent_dir_url.endswith( link ) ) :
                        continue

                    newlink = "%s/%s" % (self.url, link)
                    parser = EggHTMLDirListingParser( newlink, self.formatter )

                    url_handle = self._urlutil.urlopen( newlink )

                    if( not( url_handle is None ) ) :
                        response = url_handle.read()

                        parser.feed( response )

                        self.eggs_info_dict.update( parser.get_egg_info() )



###############################################################################
## Quick test...check the official PyPI for egg packages and time it.
###############################################################################

if( __name__ == "__main__" ) :
    import time
    import urllib
    
    url = "http://cheeseshop.python.org/packages"
    formatter = EggHTMLFormatter()

    st = time.time()
    response = urllib.urlopen( url ).read()
    parser = EggHTMLPyPIParser( url, formatter )
    parser.feed( response )
    et = time.time() - st

    #print "DONE: took %s seconds" % et

    #
    # write the results to a file
    #
    fh = open( "eggs-%s" % sys.platform, "w" )

    for (egg_name, egg_info) in parser.get_egg_info() :
        fh.write( "%s: %s\n" % (egg_name, egg_info["download_url"]) )
    fh.write( "TOTAL TIME: %s\n" % et )

    fh.close()


