import random
import unittest

from enstaller.utils import comparable_version, canonical, cname_fn


class TestUtils(unittest.TestCase):

    def test_canonical(self):
        for name, cname in [
            ('NumPy', 'numpy'),
            ('MySql-python', 'mysql_python'),
            ('Python-dateutil', 'python_dateutil'),
            ('Tables', 'pytables'),
            ]:
            self.assertEqual(canonical(name), cname)

    def test_cname_fn(self):
        self.assertEqual(cname_fn('VTK-5.4.2-1.egg'), 'vtk')

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
