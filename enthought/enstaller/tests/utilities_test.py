from enthought.enstaller.utilities import *
import unittest
import os, sys

class FindEggsTest(unittest.TestCase):
    def test_find_eggs_in_scipy(self):
        # a 'hard' download page to parse
        url = 'http://sourceforge.net/project/showfiles.php?group_id=27747&package_id=19531'
        # should be something here
        self.assertNotEqual(find_eggs_in_url(url), [])