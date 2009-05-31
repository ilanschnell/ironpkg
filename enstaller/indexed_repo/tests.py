import random
import unittest

from utils import split_old_version, split_old_eggname, get_version_build


class TestUtils(unittest.TestCase):

    def test_split_old_version(self):
        self.assertEqual(split_old_version('1.1.0n3'), ('1.1.0', 3))
        self.assertEqual(split_old_version('2008cn1'), ('2008c', 1))
        self.assertEqual(split_old_version('2nn2'), ('2n', 2))
        self.assertEqual(split_old_version('1.1n'), ('1.1n', None))

    def test_split_old_eggname(self):
        fn = 'grin-1.1.1n2-py2.5.egg'
        self.assertEqual(split_old_eggname(fn), ('grin', '1.1.1', 2))
        fn = 'grin-1.1.1-py2.5.egg'
        self.assertRaises(AssertionError, split_old_eggname, fn)

    def test_get_version_build(self):
        for fn, tu in [
            ('file:///zope.interface-3.4.1n1-py2.5-macosx-10.3-fat.egg',
                ('3.4.1', 1)),
            ('local:/MySQL_python-1.2.2n3-py2.5-macosx-10.3-fat.egg',
                ('1.2.2', 3)),
            ('Reportlab-2.1n4-py2.5.egg', ('2.1', 4)),
            ('hdf5-1.8.1n13.egg', ('1.8.1', 13)),
            ('pytz-2008cn3.egg', ('2008c', 3)),
            ]:
            self.assertEqual(get_version_build(fn), tu)

        fn = 'blist-0.9.17-py2.5-win32.egg'
        self.assertRaises(AssertionError, get_version_build, fn)

    def test_matchsort(self):
        dists = [
            'numpy-1.0.4n1.egg',
            'numpy-1.2.1n1.egg',
            'numpy-1.2.1n8.egg',
            'numpy-1.2.1n11.egg',
            'numpy-1.2.1n21.egg',
            'numpy-1.3.0n1.egg',
        ]
        org = list(dists)
        random.shuffle(dists)
        dists.sort(key=get_version_build)
        self.assertEqual(dists, org)


if __name__ == '__main__':
    unittest.main()
