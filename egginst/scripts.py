import os
import sys
import re
import shutil
import zipfile
from glob import glob
from distutils.sysconfig import get_python_lib
from os.path import abspath, basename, join, islink, isfile

from utils import on_win, site_packages, rm_rf


verbose = False
bin_dir = join(sys.prefix, 'Scripts' if on_win else 'bin')


def cp_exe(dst, script_type='console_scripts'):
    if script_type == 'console_scripts':
        shutil.copyfile(join(bin_dir, 'egginst.exe'), dst)
        return
    assert script_type == 'gui_scripts'
    paths = glob(join(get_python_lib(), 'Enstaller-*.egg'))
    paths.sort()
    if not paths:
        print "WARNING: could not find Enstaller egg in %r" % get_python_lib()
        return
    z = zipfile.ZipFile(paths[-1])
    data = z.read('setuptools/gui.exe')
    z.close()
    open(dst, 'wb').write(data)


def create_proxy(src):
    if verbose:
        print "Creating proxy executable to: %r" % src
    assert src.endswith('.exe')

    dst_name = basename(src)
    if dst_name.startswith('epd-'):
        dst_name = dst_name[4:]

    dst = join(bin_dir, dst_name)
    rm_rf(dst)
    cp_exe(dst)

    dst_script = dst[:-4] + '-script.py'
    rm_rf(dst_script)
    fo = open(dst_script, 'w')
    fo.write('''\
#!"%(python)s"
# Proxy created by egginst
import sys
import subprocess

src = %(src)r

sys.exit(subprocess.call([src] + sys.argv[1:]))
''' % dict(python=sys.executable, src=src))
    fo.close()

    return dst, dst_script


def create_proxies(egg):
    for line in egg.lines_from_arcname('EGG-INFO/inst/files_to_install.txt'):
        arcname, action = line.split()
        if verbose:
            print "arcname=%r    action=%r" % (arcname, action)

        if action == 'PROXY':
            ei = 'EGG-INFO/'
            assert arcname.startswith(ei)
            src = abspath(join(egg.meta_dir, arcname[len(ei):]))
            if verbose:
                print "     src: %r" % src
            egg.files.extend(create_proxy(src))
        else:
            data = egg.z.read(arcname)
            dst = abspath(join(sys.prefix, action, basename(arcname)))
            if verbose:
                print "     dst: %r" % dst
            rm_rf(dst)
            fo = open(dst, 'wb')
            fo.write(data)
            fo.close()
            egg.files.append(dst)


def write_script(fpath, entry_pt, egg_name):
    if verbose:
        print 'Creating script: %s' % fpath

    assert entry_pt.count(':') == 1
    module, func = entry_pt.strip().split(':')
    python = sys.executable
    if on_win:
        if fpath.endswith('pyw'):
            p = re.compile('python\.exe$', re.I)
            python = p.sub('pythonw.exe', python)
        python = '"%s"' % python

    rm_rf(fpath)
    fo = open(fpath, 'w')
    fo.write('''\
#!%(python)s
# This script was created by egginst when installing:
#
#   %(egg_name)s
#
import sys
from %(module)s import %(func)s

sys.exit(%(func)s())
''' % locals())
    fo.close()
    os.chmod(fpath, 0755)


def create(egg, conf):
    for script_type in ['gui_scripts', 'console_scripts']:
        if script_type not in conf.sections():
            continue
        for name, entry_pt in conf.items(script_type):
            fname = name
            if on_win:
                exe_path = join(sys.prefix, r'Scripts\%s.exe' % name)
                rm_rf(exe_path)
                cp_exe(exe_path, script_type)
                egg.files.append(exe_path)
                fname += '-script.py'
                if script_type == 'gui_scripts':
                    fname += 'w'
            path = join(bin_dir, fname)
            write_script(path, entry_pt, basename(egg.fpath))
            egg.files.append(path)


hashbang_pat = re.compile(r'#!.+$', re.M)
def fix_script(path):
    if islink(path) or not isfile(path):
        return

    fi = open(path)
    data = fi.read()
    fi.close()

    if ' egginst ' in data:
        # This string is in the comment when write_script() creates
        # the script, so there is no need to fix anything.
        return

    m = hashbang_pat.match(data)
    if not (m and 'python' in m.group().lower()):
        return

    python = sys.executable
    if on_win:
        python = '"%s"' % python

    new_data = hashbang_pat.sub('#!' + python.replace('\\', '\\\\'),
                                data, count=1)

    if new_data == data:
        return

    if verbose:
        print "Updating: %r" % path
    fo = open(path, 'w')
    fo.write(new_data)
    fo.close()
    os.chmod(path, 0755)


def fix_scripts(egg):
    for fpath in egg.files:
        if fpath.startswith(bin_dir):
            fix_script(fpath)
