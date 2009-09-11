import random
import unittest

from requirement import Req
from dist_naming import comparable_spec, split_dist
from enstaller.utils import comparable_version


class TestUtils(unittest.TestCase):

    def test_split_dist(self):
        for repo, fn in [
            ('local:', 'foo.egg'),
            ('http://www.example.com/repo/', 'foo.egg'),
            ('file:///home/repo/', 'numpy-1.1.1-5.egg'),
            ('file://E:\\eggs\\', 'numpy-1.1.1-5.egg'),
            ('file://C:\\Desk and Top\\', 'with space.egg'),
            ]:
            dist = repo + fn
            self.assertEqual(split_dist(dist), (repo, fn))

        for dist in ['local:/foo.egg', '', 'foo.egg', 'file:///usr/']:
            self.assertRaises(AssertionError, split_dist, dist)

    def test_comparable_version(self):
        versions = ['1.0.4', '1.2.1', '1.3.0b1', '1.3.0', '1.3.10']
        org = list(versions)
        random.shuffle(versions)
        versions.sort(key=comparable_version)
        self.assertEqual(versions, org)

        versions = ['2008j', '2008k', '2009b', '2009h']
        org = list(versions)
        random.shuffle(versions)
        versions.sort(key=comparable_version)
        self.assertEqual(versions, org)

    def test_comparable_spec(self):
        s1 = comparable_spec(dict(version='2008j', build=1))
        s2 = comparable_spec(dict(version='2008j', build=2))
        s3 = comparable_spec(dict(version='2009c', build=1))
        self.assert_(s1 < s2 < s3)

        s1 = comparable_spec(dict(version='0.7.0', build=1))
        s2 = comparable_spec(dict(version='0.8.0.dev5876', build=2))
        s3 = comparable_spec(dict(version='0.8.0', build=1))
        self.assert_(s1 < s2 < s3)


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
            python = None,
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


if __name__ == '__main__':
    unittest.main()
