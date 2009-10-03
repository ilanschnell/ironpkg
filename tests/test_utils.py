import random
import unittest

from enstaller.utils import comparable_version, canonical, cname_fn


class TestUtils(unittest.TestCase):

    def test_canonical(self):
        for name, cname in [
            ('NumPy', 'numpy'),
            ('Python-dateutil', 'python_dateutil'),
            ('Tables', 'pytables'),
            ]:
            self.assertEqual(canonical(name), cname)

    def test_cname_fn(self):
        self.assertEqual(cname_fn('VTK-5.4.2-1.egg'), 'vtk')

    def test_comparable_version1(self):
        versions = ['1.0.4', '1.2.1', '1.3.0b1', '1.3.0', '1.3.10']
        org = list(versions)
        random.shuffle(versions)
        versions.sort(key=comparable_version)
        self.assertEqual(versions, org)

    def test_comparable_version2(self):
        versions = ['2008j', '2008k', '2009b', '2009h']
        org = list(versions)
        random.shuffle(versions)
        versions.sort(key=comparable_version)
        self.assertEqual(versions, org)


if __name__ == '__main__':
    unittest.main()
