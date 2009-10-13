import sys
import unittest

import enstaller.indexed_repo.dist_naming as dist_naming
from enstaller.indexed_repo.requirement import (Req, dist_as_req,
                                                add_Reqs_to_spec)


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

        self.assertEqual(dist_naming.cleanup_reponame(sys.prefix),
                         'file://' + sys.prefix +
                         ('\\' if sys.platform == 'win32' else '/'))

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
            ('0.8.0.dev19461', 3),
            ('0.8.0', 1),
            ]:
            lst.append(dist_naming.comparable_spec(dict(version=v, build=b)))

        for i in xrange(len(lst) - 1):
            self.assert_(lst[i] < lst[i + 1])


class TestReq(unittest.TestCase):

    def test_init(self):
        for req_string, name, version, build, strictness in [
            ('',          None,  None,  None, 0),
            (' \t',       None,  None,  None, 0),
            ('foo',       'foo', None,  None, 1),
            ('bar 1.9',   'bar', '1.9', None, 2),
            ('baz 1.8-2', 'baz', '1.8', 2,    3),
            ]:
            r = Req(req_string)
            self.assertEqual(r.name, name)
            self.assertEqual(r.version, version)
            self.assertEqual(r.build, build)
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
        spec = dict(metadata_version='1.1', cname='foo_bar', version='2.4.1',
                    build=3, python=None)
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

    def test_matches_py(self):
        import enstaller.indexed_repo.requirement as requirement

        spec = dict(metadata_version='1.1', cname='foo', version='2.4.1',
                    build=3, python=None)
        for py in ['2.4', '2.5', '2.6', '3.1']:
            requirement.PY_VER = py
            self.assertEqual(Req('foo').matches(spec), True)

        spec25 = dict(spec)
        spec25.update(dict(python='2.5'))

        spec26 = dict(spec)
        spec26.update(dict(python='2.6'))

        requirement.PY_VER = '2.5'
        self.assertEqual(Req('foo').matches(spec25), True)
        self.assertEqual(Req('foo').matches(spec26), False)

        requirement.PY_VER = '2.6'
        self.assertEqual(Req('foo').matches(spec25), False)
        self.assertEqual(Req('foo').matches(spec26), True)

    def test_dist_as_req(self):
        for req_string, s in [
            ('numpy', 1),
            ('numpy 1.3.0', 2),
            ('numpy 1.3.0-2', 3),
            ]:
            req = dist_as_req('file:///numpy-1.3.0-2.egg', s)
            self.assertEqual(req, Req(req_string))
            self.assertEqual(req.strictness, s)

    def test_add_Reqs_to_spec(self):
        spec = dict(name='dummy', packages=[])
        add_Reqs_to_spec(spec)
        self.assertEqual(spec['Reqs'], set())

        spec = dict(name='dumy', packages=['numpy 1.3.0'])
        add_Reqs_to_spec(spec)
        Reqs = spec['Reqs']
        self.assertEqual(len(Reqs), 1)
        self.assertEqual(Reqs, set([Req('numpy 1.3.0')]))


if __name__ == '__main__':
    unittest.main()
