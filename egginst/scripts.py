import os
import sys
import shutil
from os.path import basename, exists, join

on_Win = sys.platform.startswith('win')
BIN_DIR = join(sys.prefix, 'Scripts' if on_Win else 'bin')
CLI_EXE = join(BIN_DIR, 'egginst.exe')


def get_python():
    if on_Win:
        return '"%s"' % sys.executable
    else:
        return sys.executable


def unlink(fpath):
    if exists(dst):
        print "Warning: %r already exists, unlinking" % dst
        os.unlink(dst)


def create_proxy(src):
    print "Creating proxy executable to: %r" % src
    assert src.endswith('.exe')

    dst_name = basename(src)
    if dst_name.startswith('epd-'):
        dst_name = dst_name[4:]

    dst = join(BIN_DIR, dst_name)
    unlink(dst)
    shutil.copyfile(CLI_EXE, dst)

    dst_script = dst[:-4] + '-script.py'
    unlink(dst_script)
    fo = open(join(BIN_DIR, dst_script), 'w')
    fo.write('''\
#!%(python)s
import sys
import subprocess

src = %(src)r

sys.exit(subprocess.call([src] + sys.argv[1:]))
''' % dict(python=get_python(), src=src))
    fo.close()

    return dst, dst_script


def write_script(fpath, entry_pt, egg_name):
    print 'Creating script', fpath

    assert entry_pt.count(':') == 1
    module, func = entry_pt.strip().split(':')

    unlink(fpath)
    fo = open(fpath, 'w')
    fo.write('''\
#!%(python)s
#
#     %(egg_name)s
#
from %(module)s import %(func)s

%(func)s()
''' % dict(module=module, func=func, python=get_python(), egg_name=egg_name))
    fo.close()
    os.chmod(fpath, 0755)


def create(egg, conf):
    for name, entry_pt in conf.items("console_scripts"):
        fname = name
        if on_Win:
            exe = join(BIN_DIR, name + '.exe')
            unlink(exe)
            shutil.copyfile(CLI_EXE, exe)
            egg.files.append(exe)

            fname += '-script.py'

        fpath = join(BIN_DIR, fname)
        write_script(fpath, entry_pt, egg_name=basename(egg.fpath))
        egg.files.append(fpath)
