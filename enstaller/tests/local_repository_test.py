from enstaller.utilities import remove_eggs_from_path
from enstaller.repository import LocalRepository
from enstaller.repository import EasyInstallRepository
import unittest
import os, sys

class LocalRepositoryTest(unittest.TestCase):
    def test_site_packages(self):
        """Can we see packages in site_packages."""
        dirname = os.path.join(sys.prefix, "lib", "python2.5", "site-packages")
        repo = EasyInstallRepository(location=dirname)
        print ("Reading %s..." % dirname)
        repo.build_package_list()
        print ("done.\n")
        
        print repo.pretty_packages()
        
        #repo.pretty_print_packages(indent=4)

    def test_all_packages(self):
        """Can we see packages in site_packages."""
        repos = []
        for dirname in remove_eggs_from_path(sys.path):
            repo = EasyInstallRepository(location=dirname)
            print ("Reading %s..." % dirname)
            repo.build_package_list()
            print ("done.\n")
            
            repos.append(repo)
        
        for repo in repos:
            print repo.location
            for pkg in repo.active_packages:
                print "   ", pkg.name


if __name__ == '__main__':
    unittest.main()
