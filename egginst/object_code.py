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


placehold_pat = re.compile(5 * '/PLACEHOLD' + '([^\0\\s]*)\0')
def fix_object_code(path):
    tp = get_object_type(path)
    if tp is None:
        return

    f = open(path, 'r+b')
    data = f.read(262144)
    matches = list(placehold_pat.finditer(data))
    if not matches:
        f.close()
        return

    if verbose:
        print "Fixing placeholders in:", path
    for m in matches:
        rest = m.group(1)
        while rest.startswith('/PLACEHOLD'):
            rest = rest[10:]

        if tp.startswith('MachO-') and rest.startswith('/'):
            # deprecated: because we now use rpath on OSX as well
            r = find_lib(rest[1:])
        else:
            assert rest == '' or rest.startswith(':')
            rpaths = list(_targets)
            # extend the list with rpath which were already in the binary,
            # if any
            rpaths.extend(p for p in rest.split(':') if p)
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
