import sys
from parsers import parse_depend_index


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


_index = None
def set_index(indexfile):
    global _index

    data = open(indexfile, 'rb').read()
    _index = parse_depend_index(data)
    for spec in _index.itervalues():
        reqs = set(Req(n, vs.replace(',', ' ').split())
                   for n, vs in spec['packages'].iteritems())
        spec['Reqs'] = reqs


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
        # added it (and it's dependencies) eariler.
        if d in dists:
            continue

        # Append dependenies of the 'd', before 'd' itself.
        append_deps(dists, d)

        # Make sure we've only added dependenies and not 'd' itself, which
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

    # Start with no distributions and add all dependenies of the required
    # distribution first.
    dists = []
    append_deps(dists, d)

    # dists now has all dependenies, before adding the required distribution
    # itself, we make sure it is not listed already.
    assert d not in dists
    dists.append(d)

    return dists


def main():
    from os.path import dirname, join, isfile

    if len(sys.argv) < 3:
        print "Usage: %s indexpath requirement" % sys.argv[0]
        return

    indexpath = sys.argv[1]
    requirement = ' '.join(sys.argv[2:])

    set_index(indexpath)

    dist = get_dist(req_from_string(requirement))
    reqs = sorted(_index[dist]['Reqs'])
    for r in reqs:
        print r
    print len(reqs)

    filenames = install_order(requirement)
    index_dir = dirname(indexpath)
    for fn in filenames:
        print fn
        assert isfile(join(index_dir, fn))
    print len(filenames)


if __name__ == '__main__':
    main()
