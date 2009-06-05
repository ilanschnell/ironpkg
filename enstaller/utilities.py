#------------------------------------------------------------------------------
# Copyright (c) 2008, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Corran Webster
#------------------------------------------------------------------------------

# imports from standard library
from distutils import sysconfig
import os, sys, glob, re, platform
from os import path
from urlparse import urlsplit, urljoin
from urllib2 import urlopen
from logging import error, warning, info, debug

# imports from 3rd party libraries
from setuptools.package_index import distros_for_url
import pkg_resources

entry_patt = re.compile( "^([\w\-_]+):\ .*" )


def get_platform():
    """ Return finer-grained platform names, corresponding to supported EPD
    versions."""
    
    (PLAT, PLAT_VER) = platform.dist()[0:2]
    
    # Map RedHat to Enthought repo names
    if PLAT.lower().startswith("redhat"):
        PLAT = "redhat"
        if PLAT_VER.startswith("3"):
            PLAT_VER = "3"
        elif PLAT_VER.startswith("4"):
            PLAT_VER = "4"
        elif PLAT_VER.startswith("5"):
            PLAT_VER = "5"

    # Ubuntu returns debian...check /etc/issue too
    elif PLAT.lower().startswith("debian"):
        if path.exists("/etc/issue"):
            fh = open("/etc/issue", "r")
            lines = fh.readlines()
            fh.close()
            patt = re.compile("^([\w]+) ([\w\.]+).*")
            for line in lines:
                match = patt.match(line)
                if match is not None:
                    plat = match.group(1).lower()
                    if plat == "ubuntu":
                        PLAT = plat
                        PLAT_VER = match.group(2).lower()
                break

    # Windows
    elif sys.platform.lower().startswith("win"):
        PLAT = "windows"
        # this returns "xp" for Windows XP and "vista" for Windows Vista
        # XXX If we want to support Windows 2k we need to check this
        PLAT_VER = platform.release().lower()

    # setuptools get_platform() finds the right info for OSX
    elif sys.platform.lower().startswith("darwin"):
        (PLAT, PLAT_VER) = pkg_resources.get_platform().split( "-" )[0:2]
    
    return (PLAT, PLAT_VER)


def remove_eggs_from_path(search_path, fix_names=False):
    """
    Returns a copy of search_path with all eggs (directories or zip files)
    removed.  Eggs are identified by the ".egg" extension in the name.
    If fix_names is True, the dir names in the path are made absolute.
    Note: files with a .zip extension are removed as well.
    """
    new_path = []
    for name in search_path:
        if fix_names:
            name = os.path.normpath(path.abspath(name))
        if not (os.path.splitext(name)[-1].lower() in [".egg", ".zip"]
                or glob.glob(os.path.join(name, "*.egg-info"))):
            new_path.append(name)
            
    # If for some reason the main site-packages has .egg-info files in it, be sure to add it
    # to our path, because otherwise it would not be added.
    site_packages = sysconfig.get_python_lib()
    if site_packages not in new_path:
        new_path.append(site_packages)
    
    return new_path


def rst_table(fields, data, sorted=True, key=None, indent=0, max_width=0):
    """Print a restructured text simple table
    
        fields : a tuple of items from the data which are the column headers
            of the table
        data : a list of dictionaries, each of which will be a row in the table
        key : a sort key for the data
    """
    
    data = [tuple([str(row.get(field, '')) for field in fields])
            for row in data]
    if sorted:
        data.sort(key=key)
    for i in reversed(range(1,len(data))):
        if data[i][0] == data[i-1][0]:
            data[i] = ("",) + data[i][1:]
            
    field_sizes = [max([len(field)] + [len(row[i]) for row in data])
                   for i, field in enumerate(fields)]
    template = ' '*indent + '  '.join(["%s" for field in fields]) + '\n'
    line = template % tuple(["="*size for size in field_sizes])
    pretty_headers = tuple([field.ljust(size).replace("_", " ").title()
                            for field, size in zip(fields, field_sizes)])
    
    table = line + (template % pretty_headers) + line + \
        ''.join([template % tuple([field.ljust(size)
                                   for field, size in zip(row, field_sizes)])
                 for row in data]) + line
    if max_width:
        table = "\n".join(line[:max_width] for line in table.split('\n'))
    return table

HREF = re.compile("""href\\s*=\\s*['"']?([^'"'> ]+)""", re.I)

cache = {}


def find_eggs_in_url(url):
    """Read a URL and find any links to egg files
    
    Parameters
    ----------
    url : string
        the url to search
    
    Returns
    -------
    dists : a list of pkg_resources.Distribution objects
    """
    if url in cache:
        return cache[url]
    page = urlopen(url)
    try:
        info = page.info()
        content = page.read()
    finally:
        page.close()
    if info['Content-Type'].split(';')[0].strip() == 'text/html':
        dists = []
        for match in HREF.finditer(content):
            ref = match.group(1)
            schema, location, path, query, frag = urlsplit(ref)
            if location == '':
                ref = urljoin(url, ref)
            dists += distros_for_url(ref)
    cache[url] = dists
    return dists


def get_egg_specs_from_info(pkg_info) :
    """
    Returns a dictionary with as many keys set as possible based on the
    contents of the pkg_info string passed in
    """
    getting_depends = False
    getting_provides = False
    last_key = ""

    specs = {}
    # assume string has attributes separated by newlines
    # ...remove any Windows line ending upfront
    # XXX do we still need this?
    lines = pkg_info.replace( "\r\r\n", "\n" )
    lines = pkg_info.replace( "\r\n", "\n" )

    for line in lines.split( "\n" ) :
        # depends and provides lists have items separated by newlines,
        # lists end when a blank line is encountered
        if getting_depends:
            if line != "":
                specs["depends"].append( line )
            else :
                getting_depends = False
        elif getting_provides:
            if line != "":
                specs["provides"].append( line )
            else:
                getting_provides = False
        elif line.startswith("Depends:"):
            getting_depends = True
            specs["depends"] = []
        elif line.startswith("Provides:"):
            getting_provides = True
            specs["provides"] = []
        # if a generic entry, add to the specs dict and remember
        # the key so further lines can be added to it, until another
        # entry is encountered
        elif entry_patt.match(line):
            key, val = line.split(": ", 1)
            key = key.lower()
            specs[key] = val
            last_key = key
        # add the line to the last key if nothing else matched
        elif last_key:
            specs[last_key] += "\n%s" % line
    return specs


def run_scripts(dist, phase, dry_run=False):
    """ Run any scripts associated in the distribution with the given phase.
    """
    if dist.has_metadata("enstaller/"+phase):
        info("Running %s scripts" % phase)
        scripts = dist.get_metadata("enstaller/"+phase).split('\n')
        for line in scripts:
            script = line.strip()
            if not line or line[0] == "#":
                continue
            if not dist.has_metadata("scripts/"+script):
                warning("%s: No script named '%s' in package %s"
                        % (phase.capitalize(), script, self.name))
            if not dry_run:
                namespace = {}
                try:
                    dist.run_script(script, namespace)
                except Exception, exc:
                    error("%s: Script '%s' in package %s failed.  %s"
                            % (phase.capitalize(), script, dist.project_name,
                               exc))
            else:
                print "Run script '%s' in package %s'" % (script, dist.project_name)
    

def rmtree_error(operation, filename, exception):
    if operation == os.remove:
        error("Could not remove file %s: %s" % (filename, exception))
    elif operation == os.rmdir:
        error("Could not remove directory %s: %s" % (filename, exception))
    elif operation == os.listdir:
        error("Could not list files in directory %s: %s" % (filename, exception))
        

def query_user(msg, default=""):
    """Present a yes/no question to the user and return a response
    """

    if default:
        msg += "[%s] " % default
    response = ""
    while len(response) == 0 or response[0] not in "yn":
        response = raw_input(msg).strip().lower()
        if response == "" and default:
            response = default
    return response[0] == "y"
    

def user_select(header, data, prompt, default="1", extra_char=None,
    max_width=0):
    """Present a collection of options to the user and return a response
    """

    valid_responses = [str(i+1) for i in range(len(data))]
    if default not in valid_responses:
        valid_responses.append(default)
    if extra_char:
        valid_responses += [(str(i+1)+extra_char) for i in range(len(data))]
    for i, row in enumerate(data):
        row["option"] = str(i+1).rjust(5)
    header = ["option"] + header
    msg = rst_table(header, data, sorted=False, max_width=max_width)
    #msg = "\n".join("%4s. %s" % (i+1, option)
    #                for i, option in enumerate(option_list))
    msg += "\n\n"
    msg += prompt + "[%s] " % default
    response = ""
    while len(response) == 0 or response not in valid_responses:
        response = raw_input(msg).strip().lower()
        if response == "" and default:
            response = default
    if response != "none":
        if extra_char:
            return response
        else:
            return int(response)-1
    else:
        return None
    
