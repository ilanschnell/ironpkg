import os
import sys
import zipfile
import shutil
import tempfile
import ConfigParser
from os.path import basename, isfile, join
from distutils.sysconfig import get_python_lib

import egginst.scripts



class Dummy(object):
    pass


def fix_easy_pth(pth):
    new_lines = []
    needs_rewrite = False
    fi = open(pth)
    for line in fi:
        line = line.strip()
        if 'enstaller' in line.lower():
            needs_rewrite = True
        else:
            new_lines.append(line)
    fi.close()

    if needs_rewrite:
        fo = open(pth, 'w')
        for line in new_lines:
            fo.write(line + '\n')
        fo.close()
        print "Removed entry of Enstaller from:", pth


def main():
    """
    To bootstrap Enstaller into a Python environment, used the following
    code:

    sys.path.insert(0, '/path/to/Enstaller.egg')
    from egginst.bootstrap import main
    exitcode = main()
    """
    reload(egginst.scripts)
    reload(egginst.utils)

    sp = get_python_lib()
    egg_path = sys.path[0]

    if not isfile(egg_path):
        raise Exception("Not a file: %r" % egg_path)

    # Copy the egg into site-packages
    shutil.copy(egg_path, sp)

    # Create Enstaller.pth in site-packages
    fo = open(join(sp, 'Enstaller.pth'), 'w')
    fo.write('./%s\n' % basename(egg_path))
    fo.close()

    # Create the scripts
    egg = Dummy()
    egg.fpath = egg_path
    egg.files = []

    z = zipfile.ZipFile(egg_path)
    txt = z.read('EGG-INFO/entry_points.txt')
    z.close()

    conf = ConfigParser.ConfigParser()
    tmp_pth = join(sp, 'Enstaller_entry.txt')
    open(tmp_pth, 'w').write(txt)
    conf.read(tmp_pth)
    os.unlink(tmp_pth)

    egginst.scripts.create(egg, conf)

    # Finally, if there an easy-install.pth in site-packages, remove and
    # occurrences of Enstaller from it.
    pth = join(sp, 'easy-install.pth')
    if isfile(pth):
        fix_easy_pth(pth)

    return 0
