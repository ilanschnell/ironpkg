# Changes library path in object code (ELF and Mach-O).

import os
import sys
import re
from os.path import abspath, basename, join, islink, isfile, exists


verbose = False


# Extensions which are assumed to belong to files which don't contain
# object code
NO_OBJ = ('.py', '.pyc', '.pyo', '.h', '.a', '.c', '.txt', '.html', '.xml',
          '.png', '.jpg', '.gif')

MAGIC = {
    '\xca\xfe\xba\xbe': 'MachO-universal',
    '\xce\xfa\xed\xfe': 'MachO-i386',
    '\xcf\xfa\xed\xfe': 'MachO-x86_64',
    '\xfe\xed\xfa\xce': 'MachO-ppc',
    '\x7fELF': 'ELF',
}

# List of target direcories where shared object files are found
_targets = []


def get_object_type(fpath):
    """
    Return the object file type of the specified file (not link).
    Otherwise, if the file is not an object file, returns None.
    """
    if fpath.endswith(NO_OBJ) or islink(fpath) or not isfile(fpath):
        return None
    fi = open(fpath, 'rb')
    head = fi.read(4)
    fi.close()
    return MAGIC.get(head)


def find_lib(fn):
    for tgt in _targets:
        dst = abspath(join(tgt, fn))
        if exists(dst):
            return dst
    print "Error: library %r not found" % fn
    return join('/ERROR/path/not/found', fn)


_placehold_pat = re.compile('/PLACEHOLD' * 5 + '([^\0]*)\0')
def fix_object_code(fpath):
    tp = get_object_type(fpath)
    if tp is None:
        return

    f = open(fpath, 'r+b')
    data = f.read()
    matches = list(_placehold_pat.finditer(data))
    if not matches:
        f.close()
        return

    if verbose:
        print "Fixing placeholders in:", fpath
    for m in matches:
        gr1 = m.group(1)
        if tp.startswith('MachO') and basename(gr1) != 'PLACEHOLD':
            # Deprecated, because we now use rpath on OSX as well
            r = find_lib(basename(gr1))
        else:
            rpaths = list(_targets)
            rpaths.extend(p for p in gr1.split(os.pathsep)
                          if not p.startswith('/PLACEHOLD'))
            r = os.pathsep.join(rpaths)

        padding = len(m.group(0)) - len(r)
        if padding < 1: # we need at least one nul-character
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
        _targets.append(join(prefix, 'lib'))
        for line in egg.lines_from_arcname('EGG-INFO/inst/targets.dat'):
            _targets.append(join(prefix, line))

    if verbose:
        print 'Target directories:'
        for tgt in _targets:
            print '    %r' % tgt

    for p in egg.files:
        fix_object_code(p)
