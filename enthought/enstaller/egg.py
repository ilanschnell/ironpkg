#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Bryce Hendrix - 2007-02-08
#------------------------------------------------------------------------------

import os
import zipfile


class Egg(object):
    def __init__(self, path):
        self._path = path

        # todo: figure out a better way to set this, maybe based on other meta values?
        self.standalone_app = False

        self.name = 'unknown'
        self.version = ''
        self.summary = ''
        self.home_page = ''
        self.author = ''
        self.author_email = ''
        self.license = ''
        self.description = ''
        self.platform = ''  
        self.native_libs = []            
        self.requires = []
        self.sources = []
        self.top_level = []
        self.zip_safe = True
        
        if os.path.exists(path):
            if os.path.isfile(path):
                self.parse_zip()
            else:
                self.parse_dir()
            
        #non standard
        self.post_install_scripts = []
                        
    def parse_zip(self):
        z = zipfile.ZipFile(self._path, 'r')
        self.parse_pkg_info(z.read('EGG-INFO/PKG-INFO'))
        try:
            self.requires = z.read('EGG-INFO/requires.txt').split('\n')
        except:
            self.requires = []
        try:
            self.native_libs = z.read('EGG-INFO/native_libs.txt').split('\n')
        except:
            self.native_libs = []
        self.sources = z.read('EGG-INFO/SOURCES.txt').split('\n')
        
        self.top_level = z.read('EGG-INFO/top_level.txt').strip()
        if 'EGG-INFO/zip_safe' in z.namelist():
            self.zip_safe = True
        else:
            self.zip_safe = False
        z.close()

        #strip the extra whitespace
        for i in range(len(self.requires)):
            self.requires[i] = self.requires[i].strip()
        for i in range(len(self.native_libs)):
            self.native_libs[i] = self.native_libs[i].strip()
        for i in range(len(self.sources)):
            self.sources[i] = self.sources[i].strip()

        return
        
    def parse_dir(self, egg_info_dir='EGG-INFO'):
        f = open( os.path.join(self._path, egg_info_dir, 'PKG-INFO'), 'r' )
        self.parse_pkg_info(f.read())
        f.close()
        
        requires_file = os.path.join(self._path, egg_info_dir, 'requires.txt')
        if os.path.exists(requires_file):
            f = open( requires_file, 'r' )
            self.requires = f.readlines()
            f.close()
        else:
            self.requires = []

        native_libs_file = os.path.join(self._path, egg_info_dir, 'native_libs.txt')
        if os.path.exists(native_libs_file):
            f = open( native_libs_file, 'r' )
            self.native_libs = f.readlines()
            f.close()
        else:
            self.native_libs = []

        f = open( os.path.join(self._path, egg_info_dir, 'SOURCES.txt'), 'r' )
        self.sources = f.readlines()
        f.close()

        f = open( os.path.join(self._path, egg_info_dir, 'top_level.txt'), 'r' )
        self.top_level = f.read().strip()
        f.close()
        
        if os.path.exists(os.path.join(self._path, egg_info_dir, 'zip_safe')):
            self.zip_safe = True
        else:
            self.zip_safe = False

        #strip the extra whitespace
        for i in range(len(self.requires)):
            self.requires[i] = self.requires[i].strip()
        for i in range(len(self.native_libs)):
            self.native_libs[i] = self.native_libs[i].strip()
        for i in range(len(self.sources)):
            self.sources[i] = self.sources[i].strip()

        return

    def parse_pkg_info(self, buffer):
        lines = buffer.split('\n')
        last_line = None
        for line in lines:
            if line.startswith('Metadata-Version:'):
                pass
            elif line.startswith('Name:'):
                self.name = line[5:].strip()
                last_line = 'name'
            elif line.startswith('Version:'):
                self.version = line[8:].strip()
                last_line = 'version'
            elif line.startswith('Summary:'):
                self.summary = line[8:].strip()
                last_line = 'summary'
            elif line.startswith('Home-page:'):
                self.home_page = line[9:].strip()
                last_line = 'home_page'
            elif line.startswith('Author:'):
                self.author = line[7:].strip()
                last_line = 'author'
            elif line.startswith('Author-email:'):
                self.author_email = line[13:].strip()
                last_line = 'author_email'
            elif line.startswith('License:'):
                self.license = line[8:].strip()
                last_line = 'license'
            elif line.startswith('Description:'):
                self.description = line[12:].strip()
                last_line = 'description'
            elif line.startswith('Platform:'):
                self.platform = line[9:].strip()
                last_line = 'platform'
            else:
                if last_line is not None:
                    line = line.replace("'", '"')
                    setattr( self, last_line, 
                        eval("self.%s + '\\n\\t' + '%s'" % (last_line, line.strip())) )
        return
        
    def create_info_file(self):
        """writes an info file used by enstaller"""
        file = open(self._path + ".info", "w")
        
        file.write(self._generate_package_info() + "\n")
        
        file.write( "\nDepends:\n" )
        for dependency in self.requires:
            file.write("%s\n" % dependency)
            
        file.write( "\nProvides:\n" )
        for source in self.sources:
            file.write("%s\n" % source)
        
        file.close()
        return
        
    def _generate_package_info(self):
        pkg_info = "Metadata-Version: 1.0\n"
        pkg_info += "Name: %s\n" % self.name
        pkg_info += "Version: %s\n" % self.version
        pkg_info += "Summary: %s\n" % self.summary
        pkg_info += "Home-page: %s\n" % self.home_page
        pkg_info += "Author: %s\n" % self.author
        pkg_info += "Author-email: %s\n" % self.author_email
        pkg_info += "License: %s\n" % self.license
        pkg_info += "Description: %s\n" % self.description
        pkg_info += "Platform: %s" % self.platform
        
        return pkg_info
        
        
    def update(self, files_from_filesystem=False):
        """ Unzips the whole egg, re-generates the meta-data, adds
            the post installs and re-zips the egg.
            
            If files_from_filesystem is True, the files are read from
            the filesystem and not the original egg. The files which will
            be copied are only those in the sources
        """
        
        if os.path.isdir(self._path):
            self._update_dir(files_from_filesystem)
        else:
            self._update_zip(files_from_filesystem)
            
    def _update_meta_filenames(self, filenames):
        
        is_dir = os.path.isdir(self._path)
        
        #
        # make sure all meta files are accounted for
        #
        for metafile in ['PKG-INFO', 'requires.txt', 'native_libs.txt', 
                        'SOURCES.txt', 'top_level.txt']:
            metafile = 'EGG-INFO/' + metafile
            if metafile not in filenames:
                filenames.append(metafile)
                
        #
        # remove the post installs, these will be added back later
        #
        for filename in filenames:
            if filename.startswith("EGG-INFO/post_install"):
                filenames.remove(filename)
        
        #
        # add the correct file for zip-safeness
        #
        if self.zip_safe:
            if 'EGG-INFO/not-zip-safe' in filenames:
                filenames.remove('EGG-INFO/not-zip-safe')
                if is_dir:
                    os.unlink(os.path.join(self._path, 'EGG-INFO/not-zip-safe'))
            if 'EGG-INFO/zip-safe' not in filenames:
                filenames.append('EGG-INFO/zip-safe')
        else:
            if 'EGG-INFO/zip-safe' in filenames:
                filenames.remove('EGG-INFO/zip-safe')
                if is_dir:
                    os.unlink(os.path.join(self._path, 'EGG-INFO/zip-safe'))
            if 'EGG-INFO/not-zip-safe' not in filenames:
                filenames.append('EGG-INFO/not-zip-safe')
            
        return filenames
        
    def _insert_post_installs(self, zip):
        #
        # insert post_install scripts
        #
        
        if len(self.post_install_scripts) > 0:
            temp_script = self.generate_post_install_script()
            
            zip.write(temp_script, os.path.join("EGG-INFO", "post_install.py"))
            for script in self.post_install_scripts:
                zip.write(script, os.path.join("EGG-INFO", "post_install", os.path.basename(script)))
            
            os.unlink(temp_script)
        
            
    def _update_dir(self, files_from_filesystem):
        import shutil
        import zipfile
        
        filenames = []
        for root, dirs, files in os.walk(self._path):
            for filename in files:
                # the files should all be relative and should have 
                # unix-style path separators
                rel_name = os.path.join(root, filename)[len(self._path)+1:]
                rel_name = rel_name.replace("\\", "/")
                filenames.append(rel_name)
                
        filenames = self._update_meta_filenames(filenames)
        
        original_name = self._path + ".original"
        os.rename(self._path, original_name)
        
        cwd = os.getcwd()
        os.chdir(original_name)
        
        new = zipfile.ZipFile(self._path, 'w', zipfile.ZIP_DEFLATED)

        for filename in filenames:
            if (filename == 'EGG-INFO/zip-safe'):
                new.write(filename, "EGG-INFO/zip-safe")
                    
            elif (filename == 'EGG-INFO/not-zip-safe'):
                new.write(filename, "EGG-INFO/not-zip-safe")
                
            elif filename == 'EGG-INFO/PKG-INFO':
                f = open(filename, 'w')
                f.write(self._generate_package_info())
                f.close()
                new.write(filename, filename)
                
            elif filename == 'EGG-INFO/requires.txt':
                f = open(filename, 'w')
                for dependency in self.requires:
                    f.write("%s\n" % dependency)
                f.close()                
                new.write(filename, filename)
                
            elif filename == 'EGG-INFO/native_libs.txt':
                f = open(filename, 'w')
                for dependency in self.native_libs:
                    f.write("%s\n" % dependency)
                f.close()                
                new.write(filename, filename)
                
            elif filename == 'EGG-INFO/SOURCES.txt':
                f = open(filename, 'w')
                for dependency in self.sources:
                    f.write("%s\n" % dependency)
                f.close()                
                new.write(filename, filename)
                
            elif filename == 'EGG-INFO/top_level.txt':
                f = open(filename, 'w')
                f.write("%s\n" % self.top_level)
                f.close()
                new.write(filename, filename)
                
            else:
                new.write(filename, filename)
            
        os.chdir(cwd)

        self._insert_post_installs(new)
        
        new.close()        
        
    def _update_zip(self, files_from_filesystem):
        import shutil
        import tempfile
        import zipfile
        
        assert(not os.path.isdir(self._path))
        
        if os.path.exists(self._path):
            original_name = self._path + ".original"
            shutil.copy(self._path, original_name)
            original = zipfile.ZipFile(original_name, 'r')
            filenames = original.namelist()
        else:
            original = None
            if files_from_filesystem:
                filenames = self.sources
            else:
                filenames = []

        filenames = self._update_meta_filenames(filenames)

        new = zipfile.ZipFile(self._path, 'w', zipfile.ZIP_DEFLATED)
        
        #
        # iterate through the existing files, updating the metadata files
        #
        
        for filename in filenames:
            temp_name = (os.path.join(tempfile.gettempdir(), "egg.file"))
            temp = open(temp_name, "wb")
            if (filename == 'EGG-INFO/zip-safe'):
                temp.close()
                new.write(temp_name, "EGG-INFO/zip-safe")
                    
            elif (filename == 'EGG-INFO/not-zip-safe'):
                temp.close()
                new.write(temp_name, "EGG-INFO/not-zip-safe")
                
            elif filename == 'EGG-INFO/PKG-INFO':
                temp.write(self._generate_package_info())
                temp.close()
                new.write(temp_name, filename)
                
            elif filename == 'EGG-INFO/requires.txt':
                for dependency in self.requires:
                    temp.write("%s\n" % dependency)
                temp.close()
                new.write(temp_name, filename)
                
            elif filename == 'EGG-INFO/native_libs.txt':
                for file in self.native_libs:
                    temp.write("%s\n" % file)
                temp.close()
                new.write(temp_name, filename)
                
            elif filename == 'EGG-INFO/SOURCES.txt':
                for file in self.sources:
                    temp.write("%s\n" % file)
                temp.close()
                new.write(temp_name, filename)
                
            elif filename == 'EGG-INFO/top_level.txt':
                temp.write("%s\n" % self.top_level)
                temp.close()
                new.write(temp_name, filename)
                
            else:
                if files_from_filesystem:
                    f = open(filename, "rb")
                    temp.write(f.read())
                    f.close()
                else:
                    temp.write(original.read(filename))
                temp.close()
                new.write(temp_name, filename)
            os.unlink(temp_name)
                
        if original is not None:
            original.close()

        self._insert_post_installs(new)
        
        new.close()
        
    def generate_post_install_script(self):
        script_code = """# post-install script
import sys
import os
from os import path
cwd = os.getcwd()
os.chdir( path.join( path.dirname( path.abspath( __file__ ) ),
                     "post_install" ) )
"""

        for script in self.post_install_scripts :
            #
            # build the command string to be executed for each script by making
            # it relative to the current dir, call python (sys.executable) if
            # its a python script, and make sure the script args are in place
            #
            rel_path_script = os.path.basename( script.split()[0] )
            script_args = script.split()[1:]

            if( os.path.splitext( rel_path_script )[1] in [".py", ".pyc"] ) :
                cmd = "%s" % rel_path_script
            else :
                cmd = rel_path_script
                
            if( script_args ) :
                cmd += " " + " ".join( script_args )

            script_code += "execfile( \"%s\" )\n" % (cmd)

        script_code += "os.chdir(cwd)\n"
        script_code += "# end of post-install script\n"
        
        import tempfile
        filename = os.path.join( tempfile.gettempdir(), "post_install.py")
        f = open(filename, "w")
        f.write(script_code)
        f.close()

        return filename
        
    def prettyprint(self):
        return "Egg info:\n" \
                + "      name: %s\n" % self.name \
                + "      version: %s\n" % self.version \
                + "      summary: %s\n" % self.summary \
                + "      home_page: %s\n" % self.home_page \
                + "      author: %s\n" % self.author \
                + "      author_email: %s\n" % self.author_email \
                + "      license: %s\n" % self.license \
                + "      description: %s\n" % self.description \
                + "      platform: %s\n" % self.platform \
                + "      requires: %s\n" % self.requires \
                + "      native_libs: %s\n" % self.requires \
                + "      sources: %s\n" % self.sources \
                + "      top_level: %s\n" % self.top_level \
                + "      zip_safe: %s\n" % self.zip_safe
