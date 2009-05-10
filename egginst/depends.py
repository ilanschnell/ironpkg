from parsers import parse_depend_index


class Req(object):
    def __init__(self, name, versions):
        assert name == name.strip()
        self.name = name

        assert all(v == v.strip() for v in versions), versions
        self.versions = set(versions)

    def __repr__(self):
        return "Req(%r, %r)" % (self.name, self.versions)


def req_from_string(s):
    assert isinstance(s, str)
    lst = s.replace(',', ' ').split()
    return Req(lst[0], lst[1:])


class Index(object):
    def __init__(self, indexfile):
        data = open(indexfile, 'rb').read()
        self.d = parse_depend_index(data)
        for spec in self.d.itervalues():
            reqs = set(Req(n, vs.replace(',', ' ').split())
                       for n, vs in spec['packages'].iteritems())
            spec['Reqs'] = reqs

    def req_from_filename(self, filename):
        spec = self.d[filename]
        return Req(spec['name'], [spec['version']])

    def matching_files(self, req):
        res = {}
        for fn, spec in self.d.iteritems():
            if spec['name'] != req.name:
                continue
            if (req.versions and not
                any(spec['version'] == v for v in req.versions)):
                continue
            res[fn] = self.d[fn]['Reqs']
        return res

    def get_match(self, req):
        matches = self.matching_files(req)
        assert len(matches) == 1, matches
        return matches.items()[0]

    def append_deps(self, files, req):
        print 'xxx', req
        match = self.get_match(req)
        print 'yyy', match
        for req in match[1]:
            print '---', req
            fn = self.get_match(req)[0]
            print '    ==>', fn
            if fn in files:
                continue
            self.append_deps(files, self.req_from_filename(fn))
            assert fn not in files
            files.append(fn)

    def install_order(self, req_string):
        req = req_from_string(req_string)
        print req
        files = []
        self.append_deps(files, req)
        files.append(self.matching_files(req).keys()[0])
        return files


if __name__ == '__main__':
    import sys
    x = Index(sys.argv[1])

    r = req_from_string(' numpy    ')
    print r
    print '++++', x.matching_files(r)

    print x.req_from_filename('pytables-2.0.4n1-py2.5-macosx-10.3-fat.egg')

    print x.install_order(' lxml 2.1.1 ')
