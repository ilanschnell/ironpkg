import os
import sys
import zipfile
import shutil
import ConfigParser
from os.path import basename, getsize, isfile, isdir, join
from distutils.sysconfig import get_python_lib

import egginst.scripts
import egginst.utils


site_dir = get_python_lib()
bin_dir = egginst.scripts.bin_dir

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
        print "Removed Enstaller entry from", basename(pth)


def create_scripts(egg_path):
    """
    Install the scripts of the Enstaller egg
    """
    # Create an egg object which we can pass to egginst.scripts.create
    egg = Dummy()
    egg.fpath = egg_path
    egg.files = []

    z = zipfile.ZipFile(egg_path)
    txt = z.read('EGG-INFO/entry_points.txt')
    z.close()

    # Create a ConfigParser object
    conf = ConfigParser.ConfigParser()
    tmp_pth = join(site_dir, 'Enstaller_entry.txt')
    open(tmp_pth, 'w').write(txt)
    conf.read(tmp_pth)
    egginst.utils.rm_rf(tmp_pth)

    # Make sure the target directory exists
    if not isdir(bin_dir):
        os.mkdir(bin_dir)

    # Create the actual scripts
    egginst.scripts.create(egg, conf)


def main():
    """
    To bootstrap Enstaller into a Python environment, used the following
    code:

    sys.path.insert(0, '/path/to/Enstaller.egg')
    from egginst.bootstrap import main
    exitcode = main()
    """
    # This is the path to the egg which we want to install.
    # Note that whoever calls this function has inserted the egg to the
    # from of sys.path
    egg_path = sys.path[0]
    egg_name = basename(egg_path)

    # Some sanity checks
    if not isfile(egg_path):
        raise Exception("Not a file: %r" % egg_path)
    assert egg_name.startswith("Enstaller-"), egg_name

    # Remove old Enstaller files which could cause problems for this
    # install, and which we don't want on the system
    for fn in ['enstaller', 'egginst', 'Enstaller.egg-link']:
        path = join(site_dir, fn)
        egginst.utils.rm_rf(path)

    # Make sure we're modules from the new Enstaller egg
    reload(egginst.scripts)
    reload(egginst.utils)

    sys.stdout.write('%9s [' % egginst.utils.human_bytes(getsize(egg_path)))

    # Copy the egg into site-packages
    dst = join(site_dir, basename(egg_path))
    egginst.utils.rm_rf(dst)
    shutil.copyfile(egg_path, dst)
    sys.stdout.write(40 * '.')

    # Create Enstaller.pth in site-packages
    fo = open(join(site_dir, 'Enstaller.pth'), 'w')
    fo.write('./%s\n' % egg_name)
    fo.close()
    sys.stdout.write(5 * '.')

    # Create the scripts
    create_scripts(egg_path)
    sys.stdout.write(20 * '.' + ']\n')
    sys.stdout.flush()

    # Finally, if there an easy-install.pth in site-packages, remove and
    # occurrences of Enstaller from it.
    pth = join(site_dir, 'easy-install.pth')
    if isfile(pth):
        fix_easy_pth(pth)

    return 0
