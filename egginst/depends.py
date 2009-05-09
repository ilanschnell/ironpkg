from parsers import parse_depend_index


class Depends(object):

    def __init__(self, indexfile):
        data = open(indexfile, 'rb').read()
        self.d = parse_depend_index(data)
        self.filenames = sorted(self.d.keys(), reverse=True)

    def matches(self, name, versions=[]):
        """
        Return the set of filenames which match a given name and possible
        versions
        """
        res = set([])
        for fn, spec in self.d.iteritems():
            if spec['name'] != name:
                continue
            if not versions or any(spec['version'] == v for v in versions):
                res.add(fn)
        return res


if __name__ == '__main__':
    import sys
    x = Depends(sys.argv[1])

    print x.matches('numpy', ['1.2.1', '1.3.0']) #, '1.2.1')

    for fn in x.matches('tables'):
        print x.pkg_deps(fn)
