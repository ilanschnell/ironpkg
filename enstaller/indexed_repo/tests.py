import random
import unittest

import dist_naming
from enstaller.utils import comparable_version
from requirement import Req, dist_as_req


class TestUtils(unittest.TestCase):

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


class TestDistNaming(unittest.TestCase):

    def test_split_dist(self):
        for repo, fn in [
            ('http://www.example.com/repo/', 'foo.egg'),
            ('file:///home/repo/', 'numpy-1.1.1-5.egg'),
            ('file://E:\\eggs\\', 'numpy-1.1.1-5.egg'),
            ('file://C:\\Desk and Top\\', 'with space.egg'),
            ]:
            dist = repo + fn
            self.assertEqual(dist_naming.split_dist(dist), (repo, fn))

        for dist in ['local:/foo.egg', '', 'foo.egg', 'file:///usr/']:
            self.assertRaises(AssertionError, dist_naming.split_dist, dist)

    def test_is_valid_eggname(self):
        for fn, valid in [
            ('numpy-1.3.4-7.egg', True),
            ('numpy-1.3.4n7-py2.5.egg', False),
            ('numpy-1.3.4-172.egg', True),
            ('numpy-1.3.4-py2.5-win32.egg', False),
            ]:
            self.assertEqual(dist_naming.is_valid_eggname(fn), valid)

    def test_split_eggname(self):
        for fn, nvb in [
            ('numpy-1.3.4-7.egg', ('numpy', '1.3.4', 7)),
            ('python_dateutil-0.5-12.egg', ('python_dateutil', '0.5', 12)),
            ]:
            self.assertEqual(dist_naming.split_eggname(fn), nvb)

    def test_cleanup_reponame(self):
        for repo, a in [
            ('http://www.example.com/repo', '/'),
            ('http://www.example.com/repo/', ''),
            ('file:///home/repo', '/'),
            ('file:///home/repo/', ''),
            ('file://E:\\eggs', '\\'),
            ('file://E:\\eggs\\', ''),
            ('file://C:\\Desk and Top', '\\'),
            ]:
            self.assertEqual(dist_naming.cleanup_reponame(repo), repo + a)

    def test_comparable_spec1(self):
        cs = dist_naming.comparable_spec
        s1 = cs(dict(version='2008j', build=1))
        s2 = cs(dict(version='2008j', build=2))
        s3 = cs(dict(version='2009c', build=1))
        self.assert_(s1 < s2 < s3)

    def test_comparable_spec2(self):
        lst = []
        for v, b in [
            ('0.7.0', 1),
            ('0.8.0.dev4657', 2),
            ('0.8.0.dev5876', 1),
            ('0.8.0.dev9461', 3),
            ('0.8.0', 1),
            ]:
            lst.append(dist_naming.comparable_spec(dict(version=v, build=b)))

        for i in xrange(len(lst) - 1):
            self.assert_(lst[i] < lst[i + 1])


class TestReq(unittest.TestCase):

    def test_init(self):
        for req_string, name, version, strictness in [
            ('', None, None, 0),
            ('foo', 'foo', None, 1),
            ('bar 1.9', 'bar', '1.9', 2),
            ('baz 1.8-2', 'baz', '1.8-2', 3),
            (' bazar  1.8-2 ', 'bazar', '1.8-2', 3),
            ]:
            r = Req(req_string)
            self.assertEqual(r.name, name)
            self.assertEqual(r.version, version)
            self.assertEqual(r.strictness, strictness)

    def test_misc_methods(self):
        for req_string in ['', 'foo', 'bar 1.2', 'baz 2.6.7-5']:
            r = Req(req_string)
            self.assertEqual(str(r), req_string)
            self.assertEqual(r, r)
            self.assertEqual(eval(repr(r)), r)

        self.assertNotEqual(Req('foo'), Req('bar'))
        self.assertNotEqual(Req('foo 1.4'), Req('foo 1.4-5'))

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

    def test_dist_as_req(self):
        for req_string, s in [
            ('numpy', 1),
            ('numpy 1.3.0', 2),
            ('numpy 1.3.0-2', 3),
            ]:
            req = dist_as_req('file:///numpy-1.3.0-2.egg', s)
            self.assertEqual(req, Req(req_string))
            self.assertEqual(req.strictness, s)


if __name__ == '__main__':
    unittest.main()
