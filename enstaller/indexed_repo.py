import sys
import re
import os
import bz2
import string
import hashlib
import zipfile
from collections import defaultdict
from os.path import abspath, basename, dirname, join, isfile


def parse_metadata(data, var_names=None):
    """
    Given the content of a dependency file, return a dictionary mapping the
    variables to their values, optionally filtered by var_names.
    """
    d = {}
    exec data in d
    if var_names is None:
        return d

    d2 = {}
    for name in var_names:
        d2[name] = d[name]
    return d2


def parse_index(data):
    """
    Given the bz2 compressed data of an index file, return a dictionary
    mapping the distribution names to the content of the cooresponding
    section.
    """
    data = bz2.decompress(data)

    d = defaultdict(list)
    sep_pat = re.compile(r'==>\s+(\S+)\s+<==')
    for line in data.splitlines():
        m = sep_pat.match(line)
        if m:
            fn = m.group(1)
            continue
        d[fn].append(line.rstrip())

    d2 = {}
    for k in d.iterkeys():
        d2[k] = '\n'.join(d[k])

    return d2


_DEPEND_VARS = [
    'metadata_version', 'md5', 'name', 'version', 'disttype',
    'arch', 'platform', 'osdist', 'python', 'packages',
]
def parse_depend_index(data):
    """
    Given the data of index-depend.bz2, return a dict mapping each distname
    to a dict mapping variable names to their values.
    """
    d = parse_index(data)
    for k in d.iterkeys():
        d[k] = parse_metadata(d[k], _DEPEND_VARS)
    return d



class Req(object):
    def __init__(self, name, versions):
        self.name = self.canonical(name)
        self.versions = sorted(versions)

    def canonical(self, s):
        """
        Return a canonical representations of a project name.  This is
        necessary for finding matches.
        """
        s = s.lower()
        s = s.replace('-', '_')
        if s == 'tables':
            s = 'pytables'
        return s

    def matches(self, name, version):
        """
        Returns True if the name and version of a distribution matches the
        requirement (self).  That is, the canonical name must match, and
        the version must be in the list of requirement versions.
        """
        assert isinstance(version, str)

        if self.canonical(name) != self.name:
            return False
        if self.versions == []:
            return True
        return version in self.versions

    def __repr__(self):
        return "Req(%r, %r)" % (self.name, self.versions)

    def __cmp__(self, other):
        tmp = cmp(self.name, other.name)
        if tmp != 0:
            return tmp
        # names are equal compare versions
        return cmp(self.versions, other.versions)


def req_from_string(s):
    """
    Return a requirement object from a string such as:
    'numpy', 'numpy 1.3.0', 'numpy 1.2.1, 1.3.0'
    the optional comma between versions meaning "or".
    """
    lst = s.replace(',', ' ').split()
    return Req(lst[0], lst[1:])


def add_Reqs(spec):
    """
    add the 'Reqs' key to a spec dictionary.
    """
    reqs = set(Req(n, vs.replace(',', ' ').split())
               for n, vs in spec['packages'].iteritems())
    spec['Reqs'] = reqs


_old_version_pat = re.compile(r'(\S+?)(n\d+)$')
def split_old_version(version):
    """
    Return tuple(version, build) for an old 'n' version.
    """
    m = _old_version_pat.match(version)
    if m is None:
        return version, None
    return m.group(1), int(m.group(2)[1:])

def split_old_eggname(eggname):
    assert basename(eggname) == eggname and eggname.endswith('.egg')
    name, old_version = eggname[:-4].split('-')[:2]
    version, build = split_old_version(old_version)
    assert build is not None
    return name, version, build

def get_buildnumber(url):
    """
    Return the build number of an "old" style named egg.
    """
    eggname = basename(url)
    return split_old_eggname(eggname)[2]


def download_data(url):
    """
    Downloads data from the url, returns the data as a string.
    """
    from setuptools.package_index import open_with_auth

    print "downloading data from: %r" % url
    handle = open_with_auth(url)
    data = handle.read()
    handle.close()

    print "downloaded %i bytes" % len(data)

    return data


def get_data_from_url(url, md5=None):
    """
    Get data from a url and check optionally check the MD5.
    """
    if url.startswith('file://'):
        index_path = url[7:]
        data = open(index_path).read()

    elif url.startswith('http://'):
        data = download_data(url)

    else:
        raise Exception("Not valid url: " + url)

    if md5 is not None:
        assert hashlib.md5(data).hexdigest() == md5, url

    return data


class IndexedRepo(object):

    def __init__(self):
        """
        Initialize the index.
        """
        # Local directory
        self.path = '.'

        # chain of repos, either local or remote, from which distributions
        # may be fetched
        self.chain = []

        # maps distributions to specs
        self.index = {}

    def add_repo(self, url_dir):
        """
        Add a repo to the list of extra repos, i.e. read the index file of
        the url, parse it and update the index.
        """
        print "Adding repo:", url_dir
        assert url_dir.endswith('/'), url_dir
        assert url_dir not in self.chain, url_dir
        self.chain.append(url_dir)

        data = get_data_from_url(join(url_dir, 'index-depend.bz2'))

        index2 = parse_depend_index(data)
        for spec in index2.itervalues():
            add_Reqs(spec)

        for distname, spec in index2.iteritems():
            dist = join(url_dir, distname)
            assert dist not in self.index
            self.index[dist] = spec

    def dist_from_chain(self, distname):
        for url_dir in self.chain:
            dist = join(url_dir, distname)
            if dist in self.index:
                return dist
        raise Exception("distname=%r not found in chain=%r" %
                        (distname, self.chain))

    def fetch_dist(self, distname):
        """
        Get a distribution from the first item in the chain which lists it.
        """
        if distname in os.listdir(self.path):
            raise Exception("distribution %r in local directory" % distname)

        dist = self.dist_from_chain(distname)

        data = get_data_from_url(dist, self.index[dist]['md5'])

        dst = join(self.path, distname)
        print "Copying %r to %r" % (dist, dst)
        fo = open(dst, 'wb')
        fo.write(data)
        fo.close()

    def get_dist(self, req):
        """
        Return a list of distributions matching the requirement.
        The list is sorted, such that the first element in the list is
        the most recent.
        """
        lst1 = []
        for dist, spec in self.index.iteritems():
            if req.matches(spec['name'], spec['version']):
                lst1.append(dist)

        if not lst1:
            raise Exception("ERROR: No matches found for %s" % req)

        lst2 = []
        for distname in set([basename(dist) for dist in lst1]):
            if distname in os.listdir(self.path):
                lst2.append(dist)

            else:
                lst2.append(self.dist_from_chain(distname))

        assert lst2 is not []
        lst2.sort(reverse=True, key=get_buildnumber)
        return lst2[0]

    def reqs_dist(self, dist):
        """
        Return the requirement objects (as a sorted list) which are a
        distribution requires.
        """
        return sorted(self.index[dist]['Reqs'])

    def append_deps(self, dists, dist):
        """
        Append distributions required by (the distribution) 'dist' to the list
        recursively.
        """
        # first we need to know what the requirements of 'dist' are, we sort
        # them to because we want the list of distributions to be
        # deterministic.
        for r in self.reqs_dist(dist):
            # This is the distribution we finally want to append
            d = self.get_dist(r)

            # if the distribution 'd' is already in the list, we have already
            # added it (and it's dependencies) earlier.
            if d in dists:
                continue

            # Append dependencies of the 'd', before 'd' itself.
            self.append_deps(dists, d)

            # Make sure we've only added dependencies and not 'd' itself, which
            # could happen if there a loop is the dependency tree.
            assert d not in dists

            # Append the distribution itself.
            dists.append(d)

    def install_order(self, req_string):
        """
        Return the list of distributions which need to be installed to meet
        the requirement.
        The returned list is given in dependency order, i.e. the distributions
        can be installed in this order without any package being installed
        before its dependencies got installed.
        """
        req = req_from_string(req_string)

        # This is the actual distribution we append at the end
        d = self.get_dist(req)

        # Start with no distributions and add all dependencies of the required
        # distribution first.
        dists = []
        self.append_deps(dists, d)

        # dists now has all dependencies, before adding the required
        # distribution itself, we make sure it is not listed already.
        assert d not in dists
        dists.append(d)

        return dists

    def add_dist(self, distname):
        """
        Add an unindexed distribution (egg), which must already exist in the
        repository, to the index (in memory).  Note that the index file on
        disk remains untouched.
        """
        print "Added %r to index" % distname

        if distname != basename(distname):
            raise Exception("base filename expected, got %r" % distname)

        if distname in self.index:
            raise Exception("%r already exists in index" % distname)

        arcname = 'EGG-INFO/spec/depend'
        z = zipfile.ZipFile(join(self.path, distname))
        if arcname not in z.namelist():
            z.close()
            raise Exception("arcname=%r does not exist in %r" %
                            (arcname, zip_file))

        self.index[distname] = parsers.parse_metadata(z.read(arcname),
                                                      parsers._DEPEND_VARS)
        add_Reqs(self.index[distname])
        z.close()

    def test(self, assert_files_exist=False, verbose=False):
        """
        Test the content of the repo for consistency.
        """
        allreqs = defaultdict(int)

        for fn in sorted(self.index.keys(), key=string.lower):
            if verbose:
                print fn

            if assert_files_exist:
                dist_path = join(self.path, fn)
                assert isfile(dist_path), dist_path

            spec = self.index[fn]
            for r in spec['Reqs']:
                allreqs[r] += 1
                d = self.get_dist(r)
                if verbose:
                    print '\t', r, '->', self.get_dist(r)
                assert isinstance(r.versions, list) and r.versions
                assert all(v == v.strip() for v in r.versions)
                assert d in self.index

            r = Req(spec['name'], [spec['version']])
            assert self.get_dist(r)
            if verbose:
                print

        if verbose:
            print 70 * '='
        print "Index has %i distributions" % len(self.index)
        print "The following distributions are not required anywhere:"
        for fn, spec in self.index.iteritems():
            if not any(r.matches(spec['name'], spec['version'])
                       for r in allreqs):
                print '\t%s' % fn
        print 'OK'


def main():
    from optparse import OptionParser

    p = OptionParser(
        usage="usage: %prog [options] [REQUIREMENT]",
        prog=basename(sys.argv[0]),
        description="queries and tests a repository")

    p.add_option('-u', "--url",
        action="store",
        default="",
        help="repo url to look at")

    p.add_option('-d', "--dir",
        action="store",
        default="",
        help="repo url to look at")

    p.add_option('-l', "--list",
        action="store_true",
        default=False,
        help="List the requirements the distribution meeting REQUIREMENTS")

    p.add_option('-t', "--test",
        action="store_true",
        default=False,
        help="test if repo is self contained")

    opts, args = p.parse_args()

    ir = IndexedRepo()
    if opts.dir:
        ir.add_repo('file://' + abspath(opts.dir) + '/')

    if opts.url:
        ir.add_repo(opts.url.rstrip('/') + '/')

    if opts.test:
        ir.test()
        return

    if not args:
        print "nothing to do"
        return

    # query for a requirement
    req_string = ' '.join(args)
    if opts.list:
        # list
        dist = ir.get_dist(req_from_string(req_string))
        for r in repo.reqs_dist(dist):
            print r
    else:
        # install order
        for fn in ir.install_order(req_string):
            print fn


if __name__ == '__main__':
    main()
