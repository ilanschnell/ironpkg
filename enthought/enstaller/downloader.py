import sys
import types
import re
import os
import time
from os import path
from distutils.sysconfig import get_python_lib
from tempfile import gettempdir
from getpass import getuser
from urlparse import urljoin

from enthought.enstaller.api import \
     IS_WINDOWS
from enthought.enstaller.text_io import \
     TextIO
from enthought.enstaller.url_util import \
     URLUtil

################################################################################
####  Downloader
####  
####  Downloads files from a URL or local path to a destination directory.
####  
####  Provides features for finding the latest version, or specific versions
####  of files from a local or remote repository and downloading them to a
####  target directory.  Methods for reporting the download progress are also
####  defined and overridable for different UIs.
################################################################################
class Downloader( TextIO ) :
    """
    Class containing a minimum set of utility functions for accessing packages
    from a repository.
    """

    use_cached_file_prompt = "Use the cached file eventhough the size could " + \
                             "not be verified (download may not even be " + \
                             "possible otherwise) (y/n)?"

    def __init__( self, *args, **kwargs ) :
        """
        Setup some bookkepping vars, primarily for the download meter and a
        URLUtil instance for accessing URLs.
        """
        super( Downloader, self ).__init__( *args, **kwargs )
        
        self._filename_width = 32
        self._screen_width = 79 # needs to be actual screen width - 1 for Windows
        self._download_filename = ""
        self._download_starttime = 0.0
        self._download_fraction = 0.0

        self._urlutil = URLUtil( *args, **kwargs )
        

    def download_file( self, src_url, dest_dir, clobber=False ) :
        """
        Downloads or copies a file from a url to a destination dir and returns
        the path to the newly downloaded/copied file.
        If clobber is set to True, will download even if the file exists.
        """
        self._download_filename = path.basename( src_url )
        self._download_starttime = 0.0
        self._download_fraction = 0.0
        #
        # support Windows and use file:/// since a drive letter might be present
        #
        if( path.exists( src_url ) and IS_WINDOWS ) :
            src_url = "file:///%s" % src_url
            
        dest_path = path.join( dest_dir, self._download_filename )

        if( clobber or not( self.file_downloaded( src_url, dest_dir ) ) ) :

            self.log( "Downloading: %s\n" % src_url )
            self._download_report_init()
            self._download_starttime = time.time()

            ok = self._urlutil.urlretrieve( src_url, dest_path,
                                            self._download_report_progress )
            if( ok is None ) :
                raise RuntimeError, "Problem downloading %s" % src_url
            
            self._download_report_fini()

        else :
            self.log( "%s has already been downloaded" % src_url + \
                      "...skipping download.\n" )
        
        return dest_path


    def file_downloaded( self, src_url, dest_dir ) :
        """
        Returns True if the src_url has been downloaded to the dest_dir and
        *appears* to be the same (based on size, if available), otherwise False.
        """
        retval = False
        dest_path = path.join( dest_dir, path.basename( src_url ) )
        
        if( path.exists( dest_path ) ) :
            retval = True
            #
            # assume file is good, but check size if possible
            #
            statinfo = os.stat( dest_path )
            size_on_disk = statinfo.st_size
            #
            # If the URL is bad, download may not even be possible, so prompt the
            # user if they want to use the cached file at their own risk
            # (defaults to no).
            #
            url = self._urlutil.urlopen( src_url )
            if( url is None ) :

                self.log( "Cannot verify that the cached file is valid.\n" )
                if( not( self.prompt( self.use_cached_file_prompt, False ) ) ) :
                    retval = False
                else :
                    retval = True

            else :
                headers = url.info()

                if( headers.has_key( "content-length" ) ) :
                    if( long( headers["content-length"] ) != size_on_disk ) :
                        self.log( "File: %s exists, but is not " % dest_path + \
                                  "the expected size.\n" )
                        retval = False

                url.close()
                
        return retval
    
        
    def find_latest_version( self, find_links, src_file_patt ) :
        """
        Returns a tuple containg the version number and the complete url to the
        latest version of a file matching the pattern from all the urls in
        find_links.  Returns None if a file matching the pattern was not found.
        """
        if( type( find_links ) != types.ListType ) :
            find_links = [find_links]

        results = {}
        #
        # Assume the find_links are in order of preference, and since the
        # results are stored in a dictionary with versions as keys, any
        # same-versioned results will be stored as "last one wins"...so, reverse
        # the list so matching versions are taken from earlier urls in the list.
        #
        repos = find_links[:]
        repos.reverse()
        for repo in repos :
            self.debug( "Checking %s\n" % repo )
            (version, url) = self._find_latest_version( repo, src_file_patt )
            if( not( url is None ) ) :
                results[version] = url
        #
        # return the highest version url in the dict, if present
        #
        versions = results.keys()
        if( versions ) :
            versions.sort( self.version_cmp )
            return results[versions[-1]]

        return None


    @staticmethod
    def get_site_packages_dir() :
        """
        returns the path to this interps default install location
        (site-pacakges)
        """
        try :
            return path.normcase( path.normpath( get_python_lib() ) )
        except :
            raise RuntimeError, \
                  "could not find default install location (site-packages)"


    def make_cache( self, name="__enstaller_tmp" ) :
        """
        Creates a cache directory in the location specified, named after
        name then the username (if available).
        """
        location = gettempdir()
        try :
            username = getuser()
        except :
            username = ""
            
        cache = path.abspath( path.join( location, name + "_%s" % username ) )
        if( not( path.exists( cache ) ) ) :
            try :
                os.mkdir( cache )
            except :
                self.log( "Could not create cache directory: %s" % cache + \
                          "...quitting." )
                sys.exit( 1 )

        return cache


    @staticmethod
    def version_cmp( a, b ) :
        """
        Function used in comparisons on strings which represent version numbers.
        """
        a_greater = 1
        b_greater = -1
        number_letter_patt = re.compile( "([0-9]+)([a-zA-Z]?)" )
        rev_number_patt = re.compile( "[Rr][Ee]?[Vv]?([0-9]+)" )
        #
        # Return 0 if versions are equal
        #
        if( a == b ) :
            return 0
        #
        # Compare each number in the version individually by splitting on .
        #
        a_vers = re.split( "[\.\_]", a )
        b_vers = re.split( "[\.\_]", b )
        #
        # Only compare the shortest length of numbers
        #
        for i in range( min( len( a_vers ), len( b_vers ) ) ) :
            #
            # Try to compare numbers, if that fails, compare strings
            #
            try :
                a = int( a_vers[i] )
                b = int( b_vers[i] )
            except ValueError :
                a = a_vers[i]
                b = b_vers[i]
                #
                # special case if a number has a single letter after it...if the
                # numbers are equal, the version with no letter is higher.
                #
                matcha = number_letter_patt.match( a )
                matchb = number_letter_patt.match( b )
                if( matcha and matchb ) :
                    a_parts = matcha.groups()
                    b_parts = matchb.groups()
                    if( a_parts[0] == b_parts[0] ) :
                        if( a_parts[1] == "" ) : return a_greater
                        if( b_parts[1] == "" ) : return b_greater
                #
                # special case if the number is a rev number, extract the number
                #
                matcha = rev_number_patt.match( a )
                matchb = rev_number_patt.match( b )
                if( matcha and matchb ) :
                    a = int( matcha.group( 1 ) )
                    b = int( matchb.group( 1 ) )

            if( a > b ) :
                return a_greater
            elif( b > a ) :
                return b_greater
        #
        # If still equal at this point, the version string lengths must be
        # unequal so longer of the two is assumed to be greater.
        #
        if( len( a_vers ) > len( b_vers ) ) :
            return a_greater

        else :
            return b_greater


    def _download_report_fini( self ) :
        """
        Called at the end of a download...in this case, it is used to write the
        total download time to stdout.
        """
        #
        # Do this only if the logging_handle is the real stdout or if its an
        # EnstallerLogger with no buffering (assume its going to stdout).
        #
        if( (self.logging_handle == sys.__stdout__) or
            (hasattr( self.logging_handle, "copy_to_buffer" ) and
             (self.logging_handle.copy_to_buffer == False)) ) :
            screen = self.logging_handle
        else :
            return

        total_time = time.time() - self._download_starttime
        #
        # backspace 16 times since download time plus | is 16 chars.
        #
        screen.write( "\b" * 16 )
        #
        # compute the time in human-readable form and print
        #
        hours = "%02d" % (total_time / 3600)
        minutes = "%02d" % ((total_time % 3600) / 60)
        secs = ((total_time % 3600) % 60)
        seconds = "%02d.%02d" % (secs, (secs - int( secs )) * 100)
        screen.write( "| %sh:%sm:%ss" % (hours, minutes, seconds) )
        screen.write( "\n" )
        screen.flush()


    def _download_report_init( self ) :
        """
        Called whenever a download starts...in this case, it is used for
        setting up stdout to print download status.
        """
        #
        # Do this only if the logging_handle is the real stdout or if its an
        # EnstallerLogger with no buffering (assume its going to stdout).
        #
        if( (self.logging_handle == sys.__stdout__) or
            (hasattr( self.logging_handle, "copy_to_buffer" ) and
             (self.logging_handle.copy_to_buffer == False)) ) :
            screen = self.logging_handle
        else :
            return

        fnw = self._filename_width
        name_len = len( self._download_filename )
        #
        # compute the spacing and write the name
        #
        space = max( 0, fnw - name_len )
        screen.write( "%s%s|" % (self._download_filename[0:fnw],
                                 " " * space) )
        #
        # write spaces to the end of the screen, placing the cursor at the end
        #
        screen.write( " " * (self._screen_width - (fnw + 1)) )
        screen.flush()

        
    def _download_report_progress( self, block_cnt, block_size, total_size ) :
        """
        Called periodically as download progresses and is passed the current
        block count, size (bytes) per block, and total size (bytes)...in this
        case, it is used for printing download status to stdout.
        """
        #
        # Do this only if the logging_handle is the real stdout or if its an
        # EnstallerLogger with no buffering (assume its going to stdout).
        #
        if( (self.logging_handle == sys.__stdout__) or
            (hasattr( self.logging_handle, "copy_to_buffer" ) and
             (self.logging_handle.copy_to_buffer == False)) ) :
            screen = self.logging_handle
        else :
            return

        fnw = self._filename_width
        #
        # compute the percentage of the file downloaded
        #
        downloaded_bytes = block_cnt * block_size
        fraction = ((downloaded_bytes * 1.0) / total_size)
        if( fraction > 1 ) :
            fraction = 1
        #
        # compute the space for the stars and write the appropriate number
        # based on the percentage of the file downloaded and the number of
        # stars already on the screen.
        #
        star_space = (self._screen_width - (fnw + 2) - 9)
        num_stars = int( star_space * self._download_fraction )
        num_stars_to_add = int( (star_space * fraction) ) - num_stars
        #
        # backspace all the way back to the end of the existing stars:
        # 9 slots for "| 100.00%", then extra space where stars will go.
        # ...then, write the new stars
        #
        screen.write( "\b" * (9 + (star_space - num_stars)) )

        screen.write( "*" * num_stars_to_add )
        screen.write( " " * (star_space - num_stars - num_stars_to_add) )
        #
        # write the new %...add up to 2 spaces depending if >10%, or >100%
        #
        percent = fraction * 100
        screen.write( "| " )
        if( percent < 10 ) :
            screen.write( "  " )
        elif( percent < 100 ) :
            screen.write( " " )

        screen.write( "%d.%02d%%" % (percent,
                                         (percent - int( percent )) * 100) )
        screen.flush()
        #
        # update the fraction so the next iter knows if it needs more stars
        #
        if( num_stars_to_add > 0 ) :
            self._download_fraction = fraction


    href_patt = re.compile( "\<[Aa]\ +[Hh][Rr][Ee][Ff]\ *=\ *[\"\']([A-Za-z0-9\.\-\_]+)[\"\']\ *\>" )
    
    def _find_latest_version( self, src_url, src_file_patt ) :
        """
        Returns a tuple containg the version number and the complete url to the
        latest version of a file matching the pattern.  Returns a tuple of Nones
        if a file matching the pattern could not be found.

        This is used primarily for find_latest_version(), which takes a list of
        urls and iterates over them, calling this method for each and comparing
        the results to find the overall highest version.
        """
        all_files = []
        versioned_files = {}
        patt_obj = re.compile( src_file_patt )
        #
        # if this is a regular directory, look for matches in the dir listing
        #
        if( src_url.lower().startswith( "file://" ) ) :
            src_url = src_url[7:]
            if( IS_WINDOWS ) :
                src_url = src_url.strip( "/" )

        if( path.exists( src_url ) ) :
            for filename in os.listdir( src_url ) :
                match = patt_obj.match( filename )
                if( match ) :
                    self.debug( "found match: %s\n" % filename )
                    versioned_files[match.group( 1 )] = path.join( src_url,
                                                                   filename )
        #
        # if a url, look for matches in the returned html
        #
        else :
            src_url += "/"
            #
            # Return Nones (as if the request was not found) if the URL was bad
            #
            url = self._urlutil.urlopen( src_url )
            if( url is None ) :
                return (None, None)
            
            http_response = url.read()
            url.close()
            hrefs = self.href_patt.findall( http_response )
            for filename in [path.basename( hr ) for hr in hrefs] :
                match = patt_obj.match( filename )
                if( match ) :
                    self.debug( "found match: %s\n" % filename )
                    versioned_files[match.group( 1 )] = urljoin( src_url,
                                                                 filename )
        #
        # return the highest version
        #
        keys = versioned_files.keys()
        keys.sort( self.version_cmp )
        if( keys ) :
            highest_ver = keys[-1]
            self.debug( "Latest version from %s is: %s\n" \
                        % (src_url, versioned_files[highest_ver]) )
            return (highest_ver, versioned_files[highest_ver])
        else :
            return (None, None)

