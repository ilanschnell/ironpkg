from utils import canonical


class Req(object):
    def __init__(self, req_string):
        for c in '<>=':
            assert c not in req_string, req_string
        lst = req_string.replace(',', ' ').split()
        self.name = canonical(lst[0])
        assert '-' not in self.name
        self.versions = sorted(lst[1:])
        if any('-' in v for v in self.versions):
            assert len(self.versions) == 1
            assert '-' in self.versions[0]
            self.strict = True
        else:
            self.strict = False

    def matches(self, spec):
        """
        Returns True if the spec of a distribution matches the requirement
        (self).  That is, the canonical name must match, and the version
        must be in the list of required versions.
        """
        assert spec['metadata_version'] == '1.1', spec
        if canonical(spec['name']) != self.name:
            return False
        if self.versions == []:
            return True
        if self.strict:
            return '%(version)s-%(build)i' % spec == self.versions[0]
        return spec['version'] in self.versions

    def __repr__(self):
        tmp = '%s %s' % (self.name, ', '.join(self.versions))
        return 'Req(%r)' % tmp.strip()

    def __cmp__(self, other):
        assert isinstance(other, Req)
        return cmp(repr(self), repr(other))
