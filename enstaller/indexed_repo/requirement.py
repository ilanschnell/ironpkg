from utils import canonical, split_eggname, filename_dist



class Req(object):
    """
    A requirement object is initalized by a requirement string. Attributes:
    name: the canonical project name
    versions: the list of possible versions required
    strictness: the level of strictness
        0   nothing matters, anything matches
        1   name matters
        2   name and version(s) matter
        3   name, version and build matter
    """

    def __init__(self, req_string):
        for c in '<>=':
            assert c not in req_string, req_string
        lst = req_string.replace(',', ' ').split()
        self.strictness = 0
        self.name = ''

        if lst:
            self.name = canonical(lst[0])
            assert '-' not in self.name
            self.strictness = 1

        self.versions = sorted(lst[1:])
        if self.versions:
            self.strictness = 2

        if any('-' in v for v in self.versions):
            assert len(self.versions) == 1
            self.strictness = 3

    def matches(self, spec):
        """
        Returns True if the spec of a distribution matches the requirement
        (self).  That is, the canonical name must match, and the version
        must be in the list of required versions.
        """
        assert spec['metadata_version'] == '1.1', spec
        if self.strictness == 0:
            return True
        if canonical(spec['name']) != self.name:
            return False
        if self.strictness == 1:
            return True
        if self.strictness == 2:
            return spec['version'] in self.versions
        assert self.strictness == 3
        return '%(version)s-%(build)i' % spec == self.versions[0]

    def __str__(self):
        res = self.name
        if self.versions:
            res += ' ' + ', '.join(self.versions)
        return res

    def __repr__(self):
        """
        return a canonical representation of the object
        """
        return 'Req(%r)' % str(self)

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))

    def as_setuptools(self):
        if self.strictness == 0:
            raise Exception("Can't convert requirement with strictness = 0")
        if self.strictness == 1:
            return self.name
        ver = self.versions[0]
        if self.strictness == 2:
            return '%s >=%s' % (self.name, ver)
        assert self.strictness == 3
        return '%s ==%s' % (self.name, ver.replace('-', 'n'))


def add_Reqs_to_spec(spec):
    """
    Add the 'Reqs' key, which maps to a set of requirement objects,
    to a spec dictionary.
    """
    spec['Reqs'] = set(Req(s) for s in spec['packages'])


def dist_as_req(dist, strictness=3):
    """
    Return the distribution in terms of the a requirement object.
    That is: What requirement gives me the distribution?
    """
    assert strictness >= 1
    name, version, build = split_eggname(filename_dist(dist))
    req_string = name
    if strictness >= 2:
        req_string += ' %s' % version
    if strictness >= 3:
        req_string += '-%s' % build
    return Req(req_string)
