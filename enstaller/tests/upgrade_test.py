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

from enthought.enstaller.utilities import remove_eggs_from_path
from enthought.enstaller.repository import EasyInstallRepository, HTMLRepository, RepositoryUnion
from enthought.enstaller.upgrade import upgrade
import unittest
import os, sys

import logging

class UpgradeTest(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
    
    def test_local_upgrade_proposal(self):
        dirname = os.path.join(sys.prefix, "lib", "python2.5", "site-packages")
        repo = EasyInstallRepository(location=dirname)
        
        installed = dict((key, project.active_package)
                         for key, project in repo.projects.items()
                         if project.active_package != None)
        available = dict((key, project.packages)
                         for key, project in repo.projects.items())
        packages = set([repo.projects["codetools"].packages[0]])
        print [package.name for package in packages]
        
        upgrades = upgrade(packages, installed, repo)
        for proposal, reasoning in upgrades:
            print "Proposal:"
            for project in proposal:
                print "  Project:", project
                print "\n".join(reasoning[project])
                print
            print

    def test_remote_upgrade_proposal(self):
        dirname = os.path.join(sys.prefix, "lib", "python2.5", "site-packages")
        repo = EasyInstallRepository(location=dirname)
        remote_repo = HTMLRepository(location="http://pypi.python.org/simple")
        
        installed = dict((key, project.active_package)
                         for key, project in repo.projects.items()
                         if project.active_package != None)
        #available = dict((key, project.packages)
        #                 for key, project in remote_repo.projects.items())
        #available.update(dict((key, project.packages)
        #                 for key, project in repo.projects.items()))
        print remote_repo.projects["zope.error"].packages
        print remote_repo.projects["zope.error"].packages[0].distribution.requires()
        packages = set([remote_repo.projects["codetools"].packages[0]])
        print [package.name for package in packages]
        
        upgrades = upgrade(packages, installed, RepositoryUnion([repo, remote_repo]))
        for proposal, reasoning in upgrades:
            print "Proposal:"
            for project in proposal:
                print "  Project:", project
                print "\n".join(reasoning[project])
                print
            print

if __name__ == '__main__':
    unittest.main()
