import random
import unittest

from egginst.naming import canonical, name_version_fn, cname_fn
from enstaller.utils import comparable_version


class TestUtils(unittest.TestCase):

    def test_canonical(self):
        for name, cname in [
            ('NumPy', 'numpy'),
            ('MySql-python', 'mysql_python'),
            ('Python-dateutil', 'python_dateutil'),
            ]:
            self.assertEqual(canonical(name), cname)

    def test_cname_fn(self):
        self.assertEqual(cname_fn('VTK-5.4.2-1.egg'), 'vtk')

    def test_naming(self):
        for fn, name, ver, cname in [
            ('NumPy-1.5-py2.6-win32.egg', 'NumPy', '1.5-py2.6-win32', 'numpy'),
            ('NumPy-1.5-2.egg', 'NumPy', '1.5-2', 'numpy'),
            ('NumPy-1.5.egg', 'NumPy', '1.5', 'numpy'),
            ('Cython.egg', 'Cython', '', 'cython'),
            ('Foo.zip', 'Foo.zip', '', 'foo.zip'),
            ]:
            self.assertEqual(name_version_fn(fn), (name, ver))
            self.assertEqual(cname_fn(fn), cname)
            self.assertEqual(canonical(name), cname)

    def test_comparable_version(self):
        for versions in (
            ['1.0.4', '1.2.1', '1.3.0b1', '1.3.0', '1.3.10',
             '1.3.11.dev7', '1.3.11.dev12', '1.3.11.dev111',
             '1.3.11', '1.3.143',
             '1.4.0.dev7749', '1.4.0rc1', '1.4.0rc2', '1.4.0'],
            ['2008j', '2008k', '2009b', '2009h', '2010b'],
            ['0.99', '1.0a2', '1.0b1', '1.0rc1', '1.0', '1.0.1'],
            ):
            org = list(versions)
            random.shuffle(versions)
            versions.sort(key=comparable_version)
            self.assertEqual(versions, org)


if __name__ == '__main__':
    unittest.main()
