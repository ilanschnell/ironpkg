#    name           platform   osdist
_DATA = {
    'xp-32':       'win32      XP',
    'os10.4-32':   'darwin     MacOS_10.4',
    'rh3-32':      'linux2     RedHat_3',
    'rh3-64':      'linux2     RedHat_3',
    'rh5-32':      'linux2     RedHat_5',
    'rh5-64':      'linux2     RedHat_5',
    'sol10-32':    'sunos5     Solaris_10',
    'sol10-64':    'sunos5     Solaris_10',
    'u8.04-32':    'linux2     Ubuntu_8.04',
    'u8.04-64':    'linux2     Ubuntu_8.04',
    'suse10.3-32': 'linux2     SuSE_10.3',
    'suse10.3-64': 'linux2     SuSE_10.3',
}


def to_list(s):
    return s.replace(',', ' ').split()


class EnForm(object):

    def __init__(self, name, val):
        self.name = name
        self.bits = int(name.split('-')[-1])
        self.platform, self.osdist = val.split()

        if self.bits == 32:
            self.arch = 'x86'
        elif self.bits == 64:
            self.arch = 'amd64'

    def __str__(self):
        return self.name

    def __repr__(self):
        return "EnForm(%r, '%s %s')" % (self.name, self.platform, self.osdist)

    def print_details(self):
        print (30*'=' + ' %s ' + 30*'=') % self.name
        print 'name:', self.name
        print 'platform:', self.platform
        print 'osdist:', self.osdist
        print 'bits:', self.bits

    def matches(self, spec):
        for var in ['arch', 'platform', 'osdist']:
            if (var in spec and
                spec[var] is not None and
                getattr(self, var) not in to_list(spec[var])):
                return False
        return True


def init_enforms():
    global ENFORMS

    ENFORMS = {}
    for k, v in _DATA.iteritems():
        ENFORMS[k] = EnForm(k, v)

init_enforms()


def get_names(spec):
    """
    returns the set of (Enforms) names which match the requirements.
    """
    res = set()
    for e in ENFORMS.itervalues():
        if e.matches(spec):
            res.add(e.name)
    return res


if __name__ == '__main__':
    #for x in ENFORMS.itervalues():
    #    x.print_details()
    print get_names({})
    print get_names({'arch': 'amd64', 'osdist': None});
