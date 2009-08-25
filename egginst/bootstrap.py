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
    fo.write('./%s\n' + basename(egg_path))
    fo.close()

    # The rest of this function creates the scripts
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

    return 0
