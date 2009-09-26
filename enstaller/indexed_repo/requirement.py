import re
from dist_naming import split_eggname, filename_dist

from enstaller.utils import PY_VER, canonical


class Req(object):
    """
    A requirement object is initalized by a requirement string. Attributes:
    name: the canonical project name
    version: the list of possible versions required
    strictness: the level of strictness
        0   nothing matters, anything matches
        1   only the name must match
        2   name and version must match
        3   name, version and build must match
    """
    py_pat = re.compile(r'\d+\.\d+$')

    def __init__(self, req_string, py=PY_VER):
        assert self.py_pat.match(py), py
        for c in '<>=,':
            assert c not in req_string, req_string
        lst = req_string.split()
        assert len(lst) <= 2, req_string
        self.strictness = 0
        self.name = self.version = None
        if lst:
            self.name = canonical(lst[0])
            self.strictness = 1
        if len(lst) == 2:
            self.version = lst[1]
            self.strictness = 2 + bool('-' in self.version)
        self.py = py

    def matches(self, spec):
        """
        Returns True if the spec of a distribution matches the requirement
        (self).  That is, the canonical name must match, and the version
        must be in the list of required versions.
        """
        assert spec['metadata_version'] >= '1.1', spec
        if spec['python'] not in (None, self.py):
            return False
        if self.strictness == 0:
            return True
        if canonical(spec['name']) != self.name:
            return False
        if self.strictness == 1:
            return True
        if self.strictness == 2:
            return spec['version'] == self.version
        assert self.strictness == 3
        return '%(version)s-%(build)i' % spec == self.version

    def __str__(self):
        if self.strictness == 0:
            return ''
        res = self.name
        if self.version:
            res += ' ' + self.version
        return res

    def __repr__(self):
        """
        return a canonical representation of the object
        """
        return 'Req(%r, py=%r)' % (str(self), self.py)

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))


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
        req_string += '-%i' % build
    return Req(req_string)


def filter_name(reqs, name):
    """
    from the requirements 'reqs', filter those for project 'name'
    """
    return set(r for r in reqs if r.name == name)
