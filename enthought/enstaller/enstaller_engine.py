#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-02-15
#------------------------------------------------------------------------------

import os
import sys
import re
import imp
import tempfile
import shutil
from os import path
from glob import glob
from zipfile import ZipFile

from setuptools.archive_util import unpack_archive

from enthought.traits.api import \
     HasTraits, Str

from enstaller.easy_installer import EasyInstaller


class EnstallerEngine( EasyInstaller, HasTraits ) :
    """
    Performs the "core" Enstaller operations, such as install, remove,
    upgrade, de/activate, etc.
    This class extends EasyInstaller to do Enstaller-specific operations.
    """
    #
    # EGG-INFO file used when installing an egg which indicates that the .pth
    # files need to be moved "up" to the parent package.
    #
    promote_file_flag = Str( "promote-pth-files" )

    #
    # EGG-INFO file which contains paths that need to be added to the RPATH in
    # binary libs contained in an egg (non-Windows only).
    #
    rpath_additions_file = Str( "rpath_additions.txt" )


    def install( self, install_dir, packages ) :
        """
        Installs the packages (either package objects or requirement strings)
        using easy_installer, then performs any postprocessing unique to
        Enstaller (post-install scripts, rpath mods, etc.)
        """
        new_egg_paths = []
        
        if( type( packages ) != type( [] ) ) :
            packages = [packages]
        
        for package in packages :
            #
            # FIXME: do something to assure that if a package_obj is passed in
            # that the install happens from the repo in the package obj only
            #
            pkg_str = self._get_package_req_string( package )
            super( EnstallerEngine, self ).install( install_dir, pkg_str )

            for dist in self.newly_installed_dists :

                new_egg_paths.append( dist.location )

                #
                # Save the list of files installed
                #
                self._write_installed_files_file( dist.location )

                #
                # run any post-install operations or scripts in the egg
                #
                self._run_post_install( dist.location )
                #
                # promote any .pth files if the promte EGG-INFO file exists (do
                # this after post-install since post-install may generate them
                #
                new_pth_files = self._promote_pth_files_if_set( dist.location )
                #
                # make the new package visible to this interpreter
                # (this is important for bootstrapping the app)
                #
                self._rescan_pythonpath( new_pth_files )

            self.log( "Successfully installed %s\n" % pkg_str )

        return new_egg_paths
    

    def remove( self, package_objs ) :
        """
        Removes the packages represented by the package objects passed in.
        """
        retcode = 0
        if( type( package_objs ) != type( [] ) ) :
            package_objs = [package_objs]

        for package_obj in package_objs :
            package_path = path.join( package_obj.location, package_obj.fullname)
            self.log( "Removing: %s..." % package_path )

            rc = self._remove_package_file( package_path )
            if( rc != 0 ) :
                self.log( "Error: could not remove: %s\n" % package_path )
                retcode = rc
            else :
                self.log( "done.\n" )

        return retcode


    #############################################################################
    # Protected interface.
    #############################################################################

    def _build_pth_name_contents_list( self, installed_egg_path ) :
        """
        returns a list of tuples containing (filename, file_contents) strings
        used for writing the pth files for a package.  This is used primarily
        for "promoting" the pth files which involves writing them to an install
        dir and updating their contents
        """
        filename_contents_tuple_list = []
        #
        # zipfiles always use forward-slash, so build this path here for
        # use in both checks
        #
        promote_flag_file = "EGG-INFO/%s" % self.promote_file_flag

        if( path.isdir( installed_egg_path ) ) :

            if( path.exists( path.join( installed_egg_path,
                                        promote_flag_file ) ) ) :
                for pthfile in glob( path.join( installed_egg_path, "*.pth" ) ):
                    fh = open( pthfile, "r" )
                    filename_contents_tuple_list.append( (pthfile, fh.read()) )
                    fh.close()

        else :
            egg_zip = ZipFile( installed_egg_path )
            #
            # save the contents of the zip off for future reference, so it
            # dosent have to be reopened later
            #
            self._zip_contents = egg_zip.namelist()

            if( promote_flag_file in self._zip_contents ) :
                for entry in self._zip_contents :
                    #
                    # only look at the top-dir
                    #
                    if( path.dirname( entry ) == "" ) :
                        if( path.splitext( entry )[-1] == ".pth" ) :
                            filename_contents_tuple_list.append(
                                (entry, egg_zip.read( entry )) )
            egg_zip.close()

        return filename_contents_tuple_list


    def _get_installed_egg_path( self, package ) :
        """
        return the path to the installed egg based on the package (either a
        Package object or a package requirement string)
        """
        #
        # first, check if the package is the path to the actual egg...if
        # so, then simply return (this happens during bootstrap)
        #
        if( isinstance( package, basestring ) and path.exists( package ) ) :
            return package

        if( hasattr( package, "fullname" ) ) :
            location = path.join( self._install_dir, package.fullname )

        else :
            py_ver = "py%s.%s" % (sys.version_info[0], sys.version_info[1])

            info = re.split( "[=<>]+", package )
            if( len( info ) > 1 ) :
                (name, version) = info[0:2]
            else :
                (name, version) = (info[0], "*")

            matches = glob( path.join( location, "%s*.egg" % name ) )
            #
            # if more than 1 found, get the newest one
            #
            if( len( matches ) > 1 ) :
                newest_time = 0
                for egg_file in matches :
                    creation_time = os.stat( egg_file )[-1]
                    if( creation_time > newest_time ) :
                        newest_time = creation_time
                        location = egg_file

            elif( len( matches ) == 1 ) :
                location = matches[0]

            else :
                raise RuntimeError, \
                      "Could not find the path to the egg just installed!"

        return location


    def _get_package_req_string( self, package_obj ) :
        """
        returns a requirement string (name==version) suitable for use with
        easy_install from a package object, or just the name if package_obj
        is only a string
        """
        #
        # A package object will have a name and version or raw_version attr.
        # If a raw_version (the unmodified version string read in from package
        # meta-data...these may have build numbers included which are important
        # for a query) is present use it, otherwise, give a regular version str.
        #
        if( hasattr( package_obj, "name" ) and
            (hasattr( package_obj, "version" ) or
             hasattr( package_obj, "raw_version" )) ) :

            if( hasattr( package_obj, "raw_version" ) ) :
                spec = "%s==%s" % (package_obj.name, package_obj.raw_version)
            elif( hasattr( package_obj, "version" ) ) :
                spec = "%s==%s" % (package_obj.name, package_obj.version)
            return spec

        elif( isinstance( package_obj, basestring ) ) :
            return package_obj

        else :
            raise RuntimeError, \
                  "Bad package type, must be a Package obj or a string"


    def _prepend_to_rpath( self, chrpath_exe, rpath_addition, bin_file ) :
        """
        Add the rpath_addition to the binary file using chrpath...if bin_file
        is not a valid binary file, simply ignore and do nothing.
        Make sure the new RPATH has the same length by truncating the end
        to match that of the original length.
        """
        #
        # sanity check
        #
        if( rpath_addition == "" ) :
            return
        #
        # first, get the existing RPATH to prepend to
        #
        (inp, out, err) = os.popen3( "%s -l %s" % (chrpath_exe, bin_file) )
        #
        # do something only if no error...otherwise ignore silently
        #
        e = err.read()
        if( e == "" ) :
            #
            # extract the rpath from the output
            #
            val = out.read()
            if( val == "" ) :
                raise RuntimeError, \
                      "Could not change RPATH on file: %s" % bin_file + \
                      "...this egg will not function properly"

            val = val.strip( "\n" )
            (fname, rpath) = val.split( ": " )
            #
            # do something only if an rpath present (does not say "no rpath")
            #
            if( not( rpath.lower().startswith( "no " ) ) ) :
                new_rpath = rpath[rpath.index( "=" )+1:]
                #
                # build the new rpath by prepending, call chrpath and print
                # warning if call failed...keep the same size as the orig
                #
                if( new_rpath != "" ) :
                    orig_length = len( new_rpath )
                    new_rpath = \
                             "%s%s%s" % (rpath_addition, os.pathsep, new_rpath)
                    new_rpath = new_rpath[:orig_length]

                    (inp2, out2, err2) = os.popen3( "%s -r %s %s" \
                                                    % (chrpath_exe, new_rpath,
                                                       bin_file) )
                    e = err2.read()
                    if( e != "" ) :
                        raise RuntimeError, \
                              "Could not change RPATH on file: %s: %s" \
                              % (bin_file, e)
                    else :
                        print "configured %s" % bin_file
        #
        # cleanup
        #
                    inp2.close() ; out2.close() ; err2.close()
        inp.close() ; out.close() ; err.close()


    def _promote_pth_files_if_set( self, installed_egg_path ) :
        """
        Looks for an EGG-INFO file indicating if the .pth files in the egg
        need to be "promoted".  This involves writing a .pth file in the
        install dir (site-packages, for example) and fixing the contents
        to reflect the new relative directory location. Returns the names
        of the newly promoted pth files, or [] if none.
        """
        new_pth_file_names = []

        (install_dir, egg_name) = path.split( installed_egg_path )
        #
        # (re)set the zip_contents variable incase the egg is a zipfile
        #
        self._zip_contents = []
        #
        # iterate over list of pth file names and their contents in order
        # to write out each one
        #
        for (pth_name, contents) in \
                self._build_pth_name_contents_list( installed_egg_path ) :

            pth_name = path.basename( pth_name )

            #
            # the new pth file will be the name of the egg + the original
            # pth file name, in order to make unique
            #
            new_pth_file_name = path.join( install_dir,
                                           "%s__%s" % (egg_name, pth_name) )
            new_pth_file = open( new_pth_file_name, "wu" )

            new_pth_file_names.append( new_pth_file_name )

            for line in contents.split( "\n" ) :
                #
                # since zips only use /, replace any \s for checking
                #
                line = re.sub( r"\\", "/", line )
                #
                # fix the line by prepending the new egg dir or zip to the
                # line...do this only if it represents a dir in the egg
                #
                if( (line in self._zip_contents) or
                    path.exists( path.join( installed_egg_path, line ) ) ) :

                    line = path.join( egg_name, line )

                new_pth_file.write( "%s\n" % line )

            new_pth_file.close()

        return new_pth_file_names


    def _relocate_egg_binaries( self, installed_egg_path ) :
        """
        If the egg has the rpath_additions_file set, and the system has the
        chrpath package installed, the binary files in the egg (libs and
        executables) will have their RPATHs modified using chrpath.  The RPATHS
        will have the paths specified in the RPATH_FILE prepended to the
        existsing RPATH...it is assumed that there is enough space on the RPATH
        for the additional characters
        """
        rpath_additions_file = path.join( installed_egg_path, "EGG-INFO",
                                          self.rpath_additions_file )
        #
        # the path must exist, and if the egg is still zipped up this method
        # wont do anything, which is OK since eggs which need RPATH mods will
        # not be zipped
        #
        if( path.exists( rpath_additions_file ) ) :
            #
            # quit if chrpath is not installed
            #
            try :
                import chrpath
                chrpath_exe = path.join( path.dirname( chrpath.__file__ ),
                                         "chrpath" )
            except ImportError :
                print "Warning: chrpath is not installed and the" + \
                      "post-install step for this egg requires it..." + \
                      "this egg may not function properly."
                return
            #
            # get a list of dirs to add to the rpaths...these are in the
            # EGG-INFO/<rpath_additions_file> file
            # ...assume they are abs-path dirs that need the installed_egg_path
            # prepended to them to make an abs path
            #
            rpath_additions = []
            fh = open( rpath_additions_file, "r" )
            for line in fh.readlines() :
                if( line ) :
                    line = line.strip( "\n" )
                    line = line.strip( "\r" )
                    line = line.strip( "\r" )
                    rpath_additions.append(
                        path.join( installed_egg_path, line ) )
            #
            # turn the list into a search path using the platforms path sep
            #
            rpath_addition = os.pathsep.join( rpath_additions )
            #
            # try to modify every file in the egg...if they arent valid binary
            # files with RPATHS, they are silently ignored
            #
            for (root, dirs, files) in os.walk( installed_egg_path ) :
                for f in files :
                    file_to_mod = path.join( root, f )
                    self._prepend_to_rpath( chrpath_exe, rpath_addition,
                                            file_to_mod )


    def _remove_package_file( self, package_filename ) :
        """
        Finds the easy_install.pth file and removes the line containing the
        package_filename, if present, then removes the egg file or dir.
        """
        retcode = 0
        package_path = path.abspath( package_filename )
        (package_dir, package_fullname) = path.split( package_path )

        #
        # Read the file (if it exists), find the matching line and write the
        # file again without the matching line.
        #
        pth_file = path.join( package_dir, "easy-install.pth" )
        if( path.exists( pth_file ) ) :

            fh = open( pth_file, "r" )
            lines = fh.readlines()
            fh.close()

            newlines = []
            for line in lines :
                #
                # On Windows, a leading ./ is often found and is safe to remove
                # for comparisons...also, strip off the newline.
                #
                chkline = line.strip()
                if( chkline.startswith( "./" ) ) :
                    chkline = chkline[2:]
                    
                if( chkline != package_fullname ) :
                    newlines.append( line )
                    
            #
            # dont keep a pth file with no packages in it around
            #
            if( len( newlines ) <= 2 ) :
                retcode = self._rm_rf( pth_file ) or retcode

            else :
                fh = open( pth_file, "wu" )
                for line in newlines :
                    fh.write( line )
                fh.close()
        #
        # Check for a .files file and remove all files listed in it.
        #
        files_file = package_path + ".files"
        if( path.exists( files_file ) ) :
            fh = open( files_file, "r" )
            for filename in fh.readlines() :
                retcode = self._rm_rf( filename.strip() ) or retcode
            fh.close()
            retcode = self._rm_rf( files_file ) or retcode
        #
        # remove the directory or egg file
        #
        retcode = self._rm_rf( package_path ) or retcode

        return retcode


    def _rescan_pythonpath( self, new_pth_files ) :
        """
        add the newly-installed packages to the path for future imports
        by rescanning the updated easy_install.pth file and any additional
        .pth files passed in
        """
        #
        # Make sure site.py is being found in site-pacakges, since easy_install
        # will occasionally make one which enstaller finds by mistake.
        #
        lib = path.dirname( self.downloader.get_site_packages_dir() )
        (site_file, site_path, site_desc) = imp.find_module( "site", [lib] )
        site = imp.load_module( "site", site_file, site_path, site_desc )
        try :
            # python 2.4
            site.addpackage( self._install_dir, "easy-install.pth",
                             set( sys.path ) )
            for pth in new_pth_files :
                site.addpackage( self._install_dir, pth, set( sys.path ) )

        except :
            # python 2.3
            site.addpackage( self._install_dir, "easy-install.pth" )
            for pth in new_pth_files :
                site.addpackage( self._install_dir, pth )


    def _rm_rf( self, file_or_dir ) :
        """
        Removes the file or directory, returns 0 on success, 1 on failure.
        """
        retcode = 0
        try :
            if( path.exists( file_or_dir ) ) :
                if( path.isdir( file_or_dir ) ) :
                    shutil.rmtree( file_or_dir )
                else :
                    os.remove( file_or_dir )

        except (IOError, OSError), err :
            self.log( "Error: could not remove %s: %s\n" % (file_or_dir, err) )
            retcode = 1

        return retcode
    

    def _run_post_install( self, installed_egg_path ) :
        """
        run any post-install scripts in the newly-installed egg defined by the
        package passed in (the package is either a string defining a package
        name or package requirement spec, or a package object containing info
        about the package downloaded (not just installed)).
        """
        tmp_unpack_dir = ""
        #
        # first, relocate the eggs binaries if the flag is set
        #
        self._relocate_egg_binaries( installed_egg_path )

        #
        # if the egg installed is a dir, simply check the EGG-INFO subdir
        # for a post_install.py script and run it, otherwise, unzip it to
        # a temp location and do the same thing
        #
        if( path.isdir( installed_egg_path ) ) :
            egg_dir = installed_egg_path

        else :
            tmp_unpack_dir = tempfile.mkdtemp( prefix="enstaller-" )
            egg_dir = path.join( tmp_unpack_dir,
                                 path.basename( installed_egg_path ) )
            unpack_archive( installed_egg_path, egg_dir )
        #
        # check for post_install.py and run if present
        #
        pi_script = path.join( egg_dir, "EGG-INFO", "post_install.py" )
        if( path.exists( pi_script ) ) :

            try :
                execfile( pi_script, {"__file__" : pi_script} )
            except Exception, err :
                self.log( "Error: problem running post-install script %s: %s\n" \
                          % (pi_script, err) )

        #
        # cleanup if a temp extraction was done
        #
        if( tmp_unpack_dir != "" ) :
            self._rm_rf( tmp_unpack_dir )


    def _write_installed_files_file( self, egg_path ) :
        """
        Saves the list of installed files for the egg at egg_path so
        it can be completely uninstalled later.
        """
        files = self.newly_installed_files.get( egg_path, [] )

        #
        # If there is data, write the file (clobbering an old one if there),
        # otherwise do nothing.
        #
        if( len( files ) > 0 ) :
            installed_files_file = egg_path + ".files"

            if( path.exists( installed_files_file ) ) :
                self._rm_rf( installed_files_file )

            fh = open( installed_files_file, "w" )
            for line in files :
                fh.write( "%s\n" % line )
            fh.close()


        
