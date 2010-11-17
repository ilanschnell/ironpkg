# Changes library path in object code (ELF and Mach-O).

import sys
import re
from os.path import abspath, join, islink, isfile, exists


verbose = False

# alt_replace_func is an optional function, which is applied to the
# replacement string (after the placeholders haven substituted)
alt_replace_func = None


# extensions which are assumed to belong to files which don't contain
# object code
NO_OBJ = ('.py', '.pyc', '.pyo', '.h', '.a', '.c', '.txt', '.html', '.xml',
          '.png', '.jpg', '.gif')

MAGIC = {
    '\xca\xfe\xba\xbe': 'MachO-universal',
    '\xce\xfa\xed\xfe': 'MachO-i386',
    '\xcf\xfa\xed\xfe': 'MachO-x86_64',
    '\xfe\xed\xfa\xce': 'MachO-ppc',
    '\xfe\xed\xfa\xcf': 'MachO-ppc64',
    '\x7fELF': 'ELF',
}

# list of target direcories where shared object files are found
_targets = []


def get_object_type(path):
    """
    Return the object file type of the specified file (not link).
    Otherwise, if the file is not an object file, returns None.
    """
    if path.endswith(NO_OBJ) or islink(path) or not isfile(path):
        return None
    fi = open(path, 'rb')
    head = fi.read(4)
    fi.close()
    return MAGIC.get(head)


def find_lib(fn):
    for tgt in _targets:
        dst = abspath(join(tgt, fn))
        if exists(dst):
            return dst
    print "ERROR: library %r not found" % fn
    return join('/ERROR/path/not/found', fn)


placehold_pat = re.compile('(/PLACEHOLD){5,}([^\0\\s]*)\0')
def fix_object_code(path):
    tp = get_object_type(path)
    if tp is None:
        return

    f = open(path, 'r+b')
    data = f.read()
    matches = list(placehold_pat.finditer(data))
    if not matches:
        f.close()
        return

    if verbose:
        print "Fixing placeholders in:", path
    for m in matches:
        gr2 = m.group(2)

        # this should not be necessary as the regular expression is
        # evaluated from left to right, meaning that greediness of
        # the placeholder repetition comes before the greedy group2
        while gr2.startswith('/PLACEHOLD'):
            gr2 = gr2[10:]

        if tp.startswith('MachO-') and gr2.startswith('/'):
            # deprecated: because we now use rpath on OSX as well
            r = find_lib(gr2[1:])
        else:
            assert gr2 == '' or gr2.startswith(':')
            rpaths = list(_targets)
            # extend the list with rpath which were already in the binary,
            # if any
            rpaths.extend(p for p in gr2.split(':') if p)
            r = ':'.join(rpaths)

        if alt_replace_func is not None:
            r = alt_replace_func(r)

        padding = len(m.group(0)) - len(r)
        if padding < 1: # we need at least one null-character
            raise Exception("placeholder %r too short" % m.group(0))
        r += padding * '\0'
        assert m.start() + len(r) == m.end()
        f.seek(m.start())
        f.write(r)
    f.close()


def fix_files(egg):
    """
    Tries to fix the library path for all object files installed by the egg.
    """
    global _targets

    prefixes = [sys.prefix]
    if egg.prefix != sys.prefix:
        prefixes.insert(0, egg.prefix)

    _targets = []
    for prefix in prefixes:
        for line in egg.lines_from_arcname('EGG-INFO/inst/targets.dat'):
            _targets.append(join(prefix, line))
        _targets.append(join(prefix, 'lib'))

    if verbose:
        print 'Target directories:'
        for tgt in _targets:
            print '    %r' % tgt

    for p in egg.files:
        fix_object_code(p)
