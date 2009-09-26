import random
import unittest

from requirement import Req, dist_as_req
from dist_naming import comparable_spec, split_dist
from enstaller.utils import comparable_version


class TestUtils(unittest.TestCase):

    def test_split_dist(self):
        for repo, fn in [
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
        s2 = comparable_spec(dict(version='0.8.0.dev4657', build=2))
        s3 = comparable_spec(dict(version='0.8.0.dev5876', build=1))
        s4 = comparable_spec(dict(version='0.8.0.dev9461', build=3))
        s5 = comparable_spec(dict(version='0.8.0', build=1))
        self.assert_(s1 < s2 < s3 < s4 < s5)


class TestReq(unittest.TestCase):

    def test_dist_as_req(self):
        for req_string, s in [
            ('numpy', 1),
            ('numpy 1.3.0', 2),
            ('numpy 1.3.0-2', 3),
            ]:
            req = dist_as_req('file:///numpy-1.3.0-2.egg', s)
            self.assertEqual(req, Req(req_string))
            self.assertEqual(req.strictness, s)

    def test_misc_methods(self):
        for req_string, n in [
            ('', 0),
            ('foo', 1),
            ('foo 1.9', 2),
            ('foo 1.8-7', 3)
            ]:
            r = Req(req_string)
            if r.strictness >= 1:
                self.assertEqual(r.name, 'foo')
            self.assertEqual(r.strictness, n)
            self.assertEqual(str(r), req_string)
            self.assertEqual(r, r)
            self.assertEqual(eval(repr(r)), r)

    def test_version(self):
        for req_string, version in [
            ('foo 1.8', '1.8'),
            ('foo 2.3', '2.3'),
            ('foo 1.8-7', '1.8-7')
            ]:
            r = Req(req_string)
            self.assertEqual(r.version, version)

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
            ('FOO-Bar 1.8.7', False),
            ('FOO-BAR 2.4.1-3', True),
            ('FOO-Bar 2.4.1-1', False),
            ]:
            self.assertEqual(Req(req_string).matches(spec), m, req_string)

        for py in ['2.4', '2.5', '2.6', '3.1']:
            self.assertEqual(Req('foo_bar', py).matches(spec), True)

        spec['python'] = '2.5'
        self.assertEqual(Req('foo_bar', '2.5').matches(spec), True)
        self.assertEqual(Req('foo_bar', '2.6').matches(spec), False)


if __name__ == '__main__':
    unittest.main()
