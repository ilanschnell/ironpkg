import unittest

from repo import split_old_version, split_old_eggname, get_build_old_eggname


class TestRepo(unittest.TestCase):

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

    def test_get_build_old_eggname(self):
        for fn, n in [
            ('zope.interface-3.4.1n1-py2.5-macosx-10.3-fat.egg', 1),
            ('MySQL_python-1.2.2n3-py2.5-macosx-10.3-fat.egg', 3),
            ('Reportlab-2.1n4-py2.5.egg', 4),
            ]:
            self.assertEqual(get_build_old_eggname(fn), n)

        fn = 'blist-0.9.17-py2.5-win32.egg'
        self.assertRaises(AssertionError, get_build_old_eggname, fn)


if __name__ == '__main__':
    unittest.main()
