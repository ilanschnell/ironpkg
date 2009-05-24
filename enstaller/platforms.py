from setuptools.package_index import open_with_auth


def to_list(s):
    return s.replace(',', ' ').split()


class Platforms(object):
    """
    An instance represents the list of platforms which are available on
    a remote repository.
    """

    def __init__(self, url):
        self.url = url + 'platforms.txt'
        self.set_txt()
        self.set_data()

    def set_txt(self):
        handle = open_with_auth(self.url)
        self.txt = handle.read()
        handle.close()

    def set_data(self):
        self.data = {}
        for line in self.txt.splitlines():
            line = line.strip()
            if not line or line.startswith(('#', '--', 'ID')):
                continue
            row = to_list(line)
            ID = int(row[0])
            self.data[ID] = dict(
                subdir = row[1],
                arch = [row[2]],
                platform = [row[3]],
                osdist = row[4:],
                )

    def _ID_matches(self, ID, var, val):
        """
        Returns True if any value belonging to the variable matches the
        platform with the ID.
        """
        if not val:
            return True
        return any(v in self.data[ID][var] for v in to_list(val))

    def get_IDs(self, spec):
        """
        returns the set of platform IDs for which the requirements match.
        """
        res = set()
        for ID in self.data.iterkeys():
            if all(self._ID_matches(ID, var, spec[var])
                   for var in ['arch', 'platform', 'osdist']):
                res.add(ID)
        return res


if __name__ == '__main__':
    egg_root = 'http://www.enthought.com/repo/epd/eggs/'
    p = Platforms(egg_root)
    print p.txt
    print p.data[2]['subdir']
    for i in xrange(1, 9):
        print '%2i %6s %6s' % (
            i,
            p._ID_matches(i, 'arch', 'amd64'),
            p._ID_matches(i, 'osdist', 'XP, Solaris_10'))
    print "IDs:", p.get_IDs({
            'osdist': None,
            'platform': 'linux2, win32, darwin',
            'arch': None,
         })
