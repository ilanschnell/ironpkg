import random
import unittest

from utils import (split_old_version, split_old_eggname, get_version_build,
                   split_dist)
from requirement import Req


class TestUtils(unittest.TestCase):

    def test_split_dist(self):
        self.assertEqual(
            split_dist('http://www.example.com/repo/foo.egg'),
            ('http://www.example.com/repo/', 'foo.egg'))
        self.assertEqual(
            split_dist('file:///home/repo/numpy-1.1.1-5.egg'),
            ('file:///home/repo/', 'numpy-1.1.1-5.egg'))

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
            ('file:///zope.interface-3.4.1-1.egg', ('3.4.1', 1)),
            ('local:MySQL_python-1.2.2-3.egg', ('1.2.2', 3)),
            ('Reportlab-2.1-4.egg', ('2.1', 4)),
            ('hdf5-1.8.1-13.egg', ('1.8.1', 13)),
            ('pytz-2008c-3.egg', ('2008c', 3)),
            ]:
            self.assertEqual(get_version_build(fn), tu)

        fn = 'blist-0.9.17-py2.5-win32.egg'
        self.assertRaises(AssertionError, get_version_build, fn)

    def test_matchsort(self):
        dists = [
            'numpy-1.0.4-1.egg',
            'numpy-1.2.1-1.egg',
            'numpy-1.2.1-8.egg',
            'numpy-1.2.1-11.egg',
            'numpy-1.2.1-21.egg',
            'numpy-1.3.0-1.egg',
        ]
        org = list(dists)
        random.shuffle(dists)
        dists.sort(key=get_version_build)
        self.assertEqual(dists, org)


class TestReq(unittest.TestCase):

    def test_misc_methods(self):
        for req_string, n in [
            ('', 0),
            ('foo', 1),
            ('foo 1.8', 2),
            ('foo 1.8, 1.9', 2),
            ('foo 1.8-7', 3)
            ]:
            r = Req(req_string)
            if r.strictness >= 1:
                self.assertEqual(r.name, 'foo')
            self.assertEqual(r.strictness, n)
            self.assertEqual(str(r), req_string)
            self.assertEqual(r, r)
            self.assertEqual(eval(repr(r)), r)

    def test_versions(self):
        for req_string, versions in [
            ('foo 1.8', ['1.8']),
            ('foo 2.3 1.8', ['1.8', '2.3']),
            ('foo 4.0.1, 2.3, 1.8', ['1.8', '2.3', '4.0.1']),
            ('foo 1.8-7', ['1.8-7'])
            ]:
            r = Req(req_string)
            self.assertEqual(r.versions, versions)

    def test_matches(self):
        spec = dict(
            metadata_version = '1.1',
            name = 'foo-bar',
            version = '2.4.1',
            build = 3,
        )
        for req_string, m in [
            ('', True),
            ('foo', False),
            ('Foo-BAR', True),
            ('foo-Bar 2.4.1', True),
            ('foo-Bar 2.4.0 2.4.1', True),
            ('foo-Bar 2.4.0 2.4.3', False),
            ('FOO-Bar 1.8.7', False),
            ('FOO-BAR 2.4.1-3', True),
            ('FOO-Bar 2.4.1-1', False),
            ]:
            r = Req(req_string)
            self.assertEqual(r.matches(spec), m)

    def test_as_setuptools(self):
        for s1, s2 in [
            ('foo', 'foo'),
            ('bar 1.8', 'bar >=1.8'),
            ('bar 1.8 2.0', 'bar >=1.8'),
            ('baz 1.3.1-7', 'baz ==1.3.1n7')
            ]:
            r = Req(s1)
            self.assertEqual(r.as_setuptools(), s2)


if __name__ == '__main__':
    unittest.main()
