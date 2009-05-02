import os
import sys
import shutil
from os.path import basename, exists, join

from utils import on_win

BIN_DIR = join(sys.prefix, 'Scripts' if on_win else 'bin')


def cp_exe(dst):
    shutil.copyfile(join(BIN_DIR, 'easy_install.exe'), dst)


def unlink(fpath):
    if exists(fpath):
        print "Warning: %r already exists, unlinking" % fpath
        os.unlink(fpath)


def create_proxy(src):
    print "Creating proxy executable to: %r" % src
    assert src.endswith('.exe')

    dst_name = basename(src)
    if dst_name.startswith('epd-'):
        dst_name = dst_name[4:]

    dst = join(BIN_DIR, dst_name)
    unlink(dst)
    cp_exe(dst)

    dst_script = dst[:-4] + '-script.py'
    unlink(dst_script)
    fo = open(join(BIN_DIR, dst_script), 'w')
    fo.write('''\
#!"%(python)s"
import sys
import subprocess

src = %(src)r

sys.exit(subprocess.call([src] + sys.argv[1:]))
''' % dict(python=sys.executable, src=src))
    fo.close()

    return dst, dst_script


def copy_to(src, dst_dir):
    dst = abspath(join(dst_dir, basename(src)))
    print "copying: %r" % src
    print "     to: %r" % dst
    unlink(dst)
    shutil.copyfile(src, dst)
    return dst


def create_proxies(egg):
    arcname = 'EGG-INFO/inst/files_to_install.txt'
    if arcname not in egg.arcnames:
        return

    for line in egg.z.read(arcname).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        src = join(egg.meta_dir, rel_name)
        if action == 'PROXY':
            egg.files.extend(create_proxy(src))
        else:
            dst_dir = join(sys.prefix, action)
            egg.files.append(copy_to(src, dst_dir))


def write_script(fpath, entry_pt, egg_name):
    print 'Creating script', fpath

    assert entry_pt.count(':') == 1
    module, func = entry_pt.strip().split(':')
    python = sys.executable
    if on_win:
        python = '"%s"' % python

    unlink(fpath)
    fo = open(fpath, 'w')
    fo.write('''\
#!%(python)s
#
#     %(egg_name)s
#
from %(module)s import %(func)s

%(func)s()
''' % dict(module=module, func=func, python=python, egg_name=egg_name))
    fo.close()
    os.chmod(fpath, 0755)


def create(egg, conf):
    for name, entry_pt in conf.items("console_scripts"):
        fname = name
        if on_win:
            exe_path = join(BIN_DIR, name + '.exe')
            unlink(exe_path)
            cp_exe(exe_path)
            egg.files.append(exe_path)

            fname += '-script.py'

        fpath = join(BIN_DIR, fname)
        write_script(fpath, entry_pt, egg_name=basename(egg.fpath))
        egg.files.append(fpath)
