# Standard library imports.
import os
import sys
import unittest

# Enstaller imports.
from enstaller.upgrade import get_upgrade_str
from pkg_resources import compose_version_string, parse_version


class UpgradeRequirementsTest(unittest.TestCase):
    # Test various requirement string variations(without our build version number).
    def test_requirements_1(self):
        upgrade_req = get_upgrade_str('pywin32', '210')
        update_req = get_upgrade_str('pywin32', '210', upgrade=False)
        
        self.assertEqual(upgrade_req, "pywin32>210")
        self.assertEqual(update_req, "pywin32==210")
        
    def test_requirements_2(self):
        upgrade_req = get_upgrade_str('pytz', '2008c')
        update_req = get_upgrade_str('pytz', '2008c', upgrade=False)
        
        self.assertEqual(upgrade_req, "pytz>=2009")
        self.assertEqual(update_req, "pytz>2008c, <2009")
        
    def test_requirements_3(self):
        upgrade_req = get_upgrade_str('docutils', '0.5')
        update_req = get_upgrade_str('docutils', '0.5', upgrade=False)
        
        self.assertEqual(upgrade_req, "docutils>=1")
        self.assertEqual(update_req, "docutils>0.5, <1")
        
    def test_requirements_4(self):
        upgrade_req = get_upgrade_str('zope.proxy', '3.4.2')
        update_req = get_upgrade_str('zope.proxy', '3.4.2', upgrade=False)
        
        self.assertEqual(upgrade_req, "zope.proxy>=4")
        self.assertEqual(update_req, "zope.proxy>3.4.2, <4")
        
    def test_requirements_5(self):
        upgrade_req = get_upgrade_str('wxpython', '2.8.7.1')
        update_req = get_upgrade_str('wxpython', '2.8.7.1', upgrade=False)
        
        self.assertEqual(upgrade_req, "wxpython>=2.9")
        self.assertEqual(update_req, "wxpython>2.8.7.1, <2.9")
        
    def test_requirements_6(self):
        upgrade_req = get_upgrade_str('cython', '0.9.8.1.1')
        update_req = get_upgrade_str('cython', '0.9.8.1.1', upgrade=False)
        
        self.assertEqual(upgrade_req, "cython>=0.10")
        self.assertEqual(update_req, "cython>0.9.8.1.1, <0.10")
        
    def test_requirements_7(self):
        upgrade_req = get_upgrade_str('pycdf', '0.6_3b')
        update_req = get_upgrade_str('pycdf', '0.6_3b', upgrade=False)
        
        self.assertEqual(upgrade_req, "pycdf>=1")
        self.assertEqual(update_req, "pycdf>0.6_3b, <1")
        
    # Test various requirement string versions(with our build version number).
    def test_en_requirements_1(self):
        upgrade_req = get_upgrade_str('pywin32', '210num0001')
        update_req = get_upgrade_str('pywin32', '210num0001', upgrade=False)
        
        self.assertEqual(upgrade_req, "pywin32>=211")
        self.assertEqual(update_req, "pywin32>210num0001, <211")
        
    def test_en_requirements_2(self):
        upgrade_req = get_upgrade_str('pytz', '2008cnum0001')
        update_req = get_upgrade_str('pytz', '2008cnum0001', upgrade=False)
        
        self.assertEqual(upgrade_req, "pytz>=2009")
        self.assertEqual(update_req, "pytz>2008cnum0001, <2009")
        
    def test_en_requirements_3(self):
        upgrade_req = get_upgrade_str('docutils', '0.5num0001')
        update_req = get_upgrade_str('docutils', '0.5num0001', upgrade=False)
        
        self.assertEqual(upgrade_req, "docutils>=1")
        self.assertEqual(update_req, "docutils>0.5num0001, <1")
        
    def test_en_requirements_4(self):
        upgrade_req = get_upgrade_str('zope.proxy', '3.4.2num0001')
        update_req = get_upgrade_str('zope.proxy', '3.4.2num0001', upgrade=False)
        
        self.assertEqual(upgrade_req, "zope.proxy>=4")
        self.assertEqual(update_req, "zope.proxy>3.4.2num0001, <4")
        
    def test_en_requirements_5(self):
        upgrade_req = get_upgrade_str('wxpython', '2.8.7.1num0001')
        update_req = get_upgrade_str('wxpython', '2.8.7.1num0001', upgrade=False)
        
        self.assertEqual(upgrade_req, "wxpython>=2.9")
        self.assertEqual(update_req, "wxpython>2.8.7.1num0001, <2.9")
        
    def test_en_requirements_6(self):
        upgrade_req = get_upgrade_str('cython', '0.9.8.1.1num0001')
        update_req = get_upgrade_str('cython', '0.9.8.1.1num0001', upgrade=False)
        
        self.assertEqual(upgrade_req, "cython>=0.10")
        self.assertEqual(update_req, "cython>0.9.8.1.1num0001, <0.10")
        
    def test_en_requirements_7(self):
        upgrade_req = get_upgrade_str('pycdf', '0.6_3bnum0001')
        update_req = get_upgrade_str('pycdf', '0.6_3bnum0001', upgrade=False)
        
        self.assertEqual(upgrade_req, "pycdf>=1")
        self.assertEqual(update_req, "pycdf>0.6_3bnum0001, <1")
        
        
if __name__ == '__main__':
    unittest.main()