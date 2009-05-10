import sys
import string
import zipfile
from collections import defaultdict
from os.path import basename, dirname, join, isfile

import parsers


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


_index = None
_repo_dir = None
def init_index(repo_dir):
    """
    Initialize the index, i.e. open the index file, parse its data and
    create an index object, which is a dict mapping distributions to specs.
    """
    global _index, _repo_dir

    _repo_dir = repo_dir

    data = open(join(_repo_dir, 'index-depend.bz2'), 'rb').read()
    _index = parsers.parse_depend_index(data)
    for spec in _index.itervalues():
        add_Reqs(spec)


def matching_dists(req):
    """
    Return a list of distributions matching the requirement.
    The list is sorted, such that the first element in the list is
    the most recent.
    """
    res = []
    for fn, spec in _index.iteritems():
        if req.matches(spec['name'], spec['version']):
            res.append(fn)
    res.sort(reverse=True)
    return res


def get_dist(req):
    """
    Return the first (most recent) distribution matching the requirement
    """
    matches = matching_dists(req)
    if not matches:
        print 'ERROR: No matches found for', req
        sys.exit(1)
    return matches[0]


def append_deps(dists, dist):
    """
    Append distributions required by (the distribution) 'dist' to the list
    recursively.
    """
    # first we need to know what the requirements of 'dist' are, we sort them
    # to because we want the list of distributions to be deterministic.
    reqs = sorted(_index[dist]['Reqs'])

    for r in reqs:
        # This is the distribution we finally want to append
        d = get_dist(r)

        # if the distribution 'd' is already in the list, we have already
        # added it (and it's dependencies) earlier.
        if d in dists:
            continue

        # Append dependencies of the 'd', before 'd' itself.
        append_deps(dists, d)

        # Make sure we've only added dependencies and not 'd' itself, which
        # could happen if there a loop is the dependency tree.
        assert d not in dists

        # Append the distribution itself.
        dists.append(d)


def install_order(req_string):
    """
    Return the list of distributions which need to be installed to meet the
    the requirement.
    The returned list is given in dependency order, i.e. the distributions
    can be installed in this order without any package being installed
    before its dependencies got installed.
    """
    req = req_from_string(req_string)

    # This is the actual distribution we append at the end
    d = get_dist(req)

    # Start with no distributions and add all dependencies of the required
    # distribution first.
    dists = []
    append_deps(dists, d)

    # dists now has all dependencies, before adding the required distribution
    # itself, we make sure it is not listed already.
    assert d not in dists
    dists.append(d)

    return dists


def add_index(distname):
    """
    Add an unindexed distribution (egg), which must already exist in the
    repository, to the index (in memory).  Note that the index file on
    disk remains untouched.
    """
    print "Added %r to index" % distname

    if distname != basename(distname):
        raise Exception("base filename expected, got %r" % distname)

    if distname in _index:
        raise Exception("%r already exists in index" % distname)

    arcname = 'EGG-INFO/spec/depend'
    z = zipfile.ZipFile(join(_repo_dir, distname))
    if arcname not in z.namelist():
        z.close()
        raise Exception("arcname=%r does not exist in %r" %
                        (arcname, zip_file))

    _index[distname] = parsers.parse_metadata(z.read(arcname),
                                              parsers._DEPEND_VARS)
    add_Reqs(_index[distname])
    z.close()


def test_index(test_files=True, verbose=False):
    allreqs = defaultdict(int)

    for fn in sorted(_index.keys(), key=string.lower):
        if verbose:
            print fn

        if test_files:
            dist_path = join(_repo_dir, fn)
            assert isfile(dist_path), dist_path

        spec = _index[fn]
        for r in spec['Reqs']:
            allreqs[r] += 1
            d = get_dist(r)
            if verbose:
                print '\t', r, '->', get_dist(r)
            assert isinstance(r.versions, list) and r.versions
            assert d in _index

        r = Req(spec['name'], [spec['version']])
        assert len(matching_dists(r)) >= 1
        if verbose:
            print

    if verbose:
        print 70 * '='
    print "Index has %i distributions" % len(_index)
    print "The following distributions are not required anywhere:"
    for fn, spec in _index.iteritems():
        if not any(r.matches(spec['name'], spec['version']) for r in allreqs):
            print '\t%s' % fn
    print 'OK'


def main():
    if len(sys.argv) < 2:
        print "Usage: %s repo_dir [requirement]" % sys.argv[0]
        return

    repo_dir = sys.argv[1]
    init_index(repo_dir)
    if len(sys.argv) == 2:
        test_index()
        return

    requirement = ' '.join(sys.argv[2:])

#    dist = get_dist(req_from_string(requirement))
#    for r in sorted(_index[dist]['Reqs']):
#        print r

    for fn in install_order(requirement):
        print fn


if __name__ == '__main__':
    main()
