# standard module imports
import sys
from os import path
import socket
import xmlrpclib

# distutils imports
from distutils import log
from setuptools.command.easy_install import easy_install, PthDistributions

class enstaller(easy_install):
    user_options = [
        ('prefix=', None, "installation prefix"),
        ("zip-ok", "z", "install package as a zipfile"),
        ("multi-version", "m", "make apps have to require() a version"),
        ("upgrade", "U", "force upgrade (searches PyPI for latest versions)"),
        ("install-dir=", "d", "install package to DIR"),
        ("script-dir=", "s", "install scripts to DIR"),
        ("exclude-scripts", "x", "Don't install scripts"),
        ("always-copy", "a", "Copy all needed packages to install dir"),
        ("index-url=", "i", "base URL of Python Package Index"),
        ("find-links=", "f", "additional URL(s) to search for packages"),
        ("delete-conflicting", "D", "no longer needed; don't use this"),
        ("ignore-conflicts-at-my-risk", None,
            "no longer needed; don't use this"),
        ("build-directory=", "b",
            "download/extract/build in DIR; keep the results"),
        ('optimize=', 'O',
         "also compile with optimization: -O1 for \"python -O\", "
         "-O2 for \"python -OO\", and -O0 to disable [default: -O0]"),
        ('record=', None,
         "filename in which to record list of installed files"),
        ('always-unzip', 'Z', "don't install as a zipfile, no matter what"),
        ('site-dirs=','S',"list of directories where .pth files work"),
        ('editable', 'e', "Install specified packages in editable form"),
        ('no-deps', 'N', "don't install dependencies"),
        ('allow-hosts=', 'H', "pattern(s) that hostnames must match"),
        ('local-snapshots-ok', 'l', "allow building eggs from local checkouts"),
    ]
    boolean_options = [
        'zip-ok', 'multi-version', 'exclude-scripts', 'upgrade', 'always-copy',
        'delete-conflicting', 'ignore-conflicts-at-my-risk', 'editable',
        'no-deps', 'local-snapshots-ok',
    ]
    negative_opt = {'always-unzip': 'zip-ok'}
    
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
    
    def run(self):
        pass
    
    # ======================
    # Common Utility methods
    # ======================
    
    def initialize(self):
        self.read_pythonpath()
    
        
    def is_on_pythonpath(self, dirname):
        """
        Returns True if the dirname is already a local repo on self.pythonpath,
        False otherwise.
        """
        on_pythonpath = False
        dirpath = path.normcase(path.normpath(path.abspath(dirname)))
        if dirpath in [r.location for r in self.pythonpath]:
            on_pythonpath = True
        return on_pythonpath    

   
    def add_pythonpath_dir(self, repo_path) :
        """
        Adds the repo object built from scanning repo_path to the list of local
        repos on the pythonpath.
        This is used primarily when an install dir is specified that was not on
        the original pythonpath.
        """

        added = False
        if repo_path != "":
            if not self.is_on_pythonpath(repo_path):
                repo = LocalRepository(location=repo_path,
                                        verbose=self.verbose,
                                        prompting=self.prompting,
                                        logging_handle=self.logging_handle)

                self.debug( "Reading %s..." % repo_path )
                repo.build_package_list()
                self.debug( "done.\n" )
                self.pythonpath.insert( 0, repo )
                added = True
        return added


    def read_pythonpath(self):
        """
        Populates the self.pythonpath list with Repository objects, one per
        directory on sys.path.

        Note: egg directories in sys.path are not included
        """

        # Fixup the path so it is useable as a list of dirs to install to.
        pythonpath = self._remove_eggs_from_path(sys.path, fix_names=True)

        # (re)build the list of repositories on sys.path
        self.pythonpath = []

        for dirname in pythonpath:
            if path.exists(dirname):
                # Create a repo obj and add only if not already present
                if not self.is_on_pythonpath(dirname):
                    repo = LocalRepository(location=dirname,
                                           verbose=self.verbose,
                                           prompting=self.prompting,
                                           logging_handle=self.logging_handle)
                    self.debug("Reading %s..." % dirname)
                    repo.build_package_list()
                    self.debug("done.\n")
                    self.pythonpath.append(repo)

    
    def read_repositories(self, repositories=[]) :
        """
        Reads the package repos (not pythonpath repos) and builds the list of
        repo objects for future processing.  If no repositories are specified,
        all repos in find_links are read.
        """

        find_links = self.find_links
        if repositories == []:
            repositories = find_links
        else:
            for repo in repositories:
                # Do not support repos that are not in find_links for now.
                if not repo in find_links:
                    raise AssertionError, "all repos must be in find_links"

        # (re)build the list of repositories
        self.repositories = []
        for url in repositories:
            processed_urls = [r.location for r in self.repositories]
            # Create a repo obj and add only if not already present
            if not url in processed_urls:
                repo = create_repository(url,
                                         verbose=self.verbose,
                                         prompting=self.prompting,
                                         logging_handle=self.logging_handle)
                if repo is None:
                    self.log("Warning: Could not access repository at: " + \
                              "%s...skipping.\n" % url )
                else :
                    self.log( "Reading %s..." % url )
                    repo.build_package_list()
                    self.log( "done.\n" )
                    self.repositories.append( repo )


    def _remove_eggs_from_path(self, search_path, fix_names=False):
        """
        Returns a copy of search_path with all eggs (directories or zip files)
        removed.  Eggs are identified by the ".egg" extension in the name.
        If fix_names is True, the dir names in the path are made absolute.
        Note: files with a .zip extension are removed as well.
        """

        new_path = []
        for name in search_path:
            if fix_names:
                name = path.normpath(path.abspath(name))
            if not (path.splitext(name)[-1].lower() in [".egg", ".zip"]
                    or glob.glob(os.path.join(name, "*.egg-info"))):
                new_path.append(name)
        return new_path

    

def create_repository(url, verbose, prompting, logging_handle) :
    """
    Given a URL, returns an instance of the appropriate Repository object type.
    """
    repo = None
    
    remote = [url.lower().startswith(p) for p in ["http:", "https:"]]
    if True in remote:
        # check if it is a pypi-style repo by trying to access it via an
        # XMLRPC call...set the server var as well
        xmlrpc_server = xmlrpclib.Server( url )
        try :
            xmlrpc_server.package_releases("")
            repo = PypiRepository(location=url,
                                  verbose=verbose,
                                  prompting=prompting,
                                  logging_handle=logging_handle )
            repo.xmlrpc_server = xmlrpc_server
        except socket.gaierror, err :
            repo = None
        except xmlrpclib.ProtocolError :
            repo = RemoteRepository(location=url,
                                    verbose=verbose,
                                    prompting=prompting,
                                    logging_handle=logging_handle )
    else:
        # If the URL has a file:// protocol, remove it to make the URL a
        # valid local directory name.  If on Windows, make sure extra / are
        # not left before the start of a path.
        if url.lower().startswith("file://"):
            url = url[7:]
            if IS_WINDOWS:
                url = url.strip( "/" )
                    
        repo = LocalRepository(location=url,
                               verbose=verbose,
                               prompting=prompting,
                               logging_handle=logging_handle ) 
    return repo
