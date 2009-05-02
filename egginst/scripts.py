import os
import sys
import shutil
from os.path import basename, join

on_Win = sys.platform.startswith('win')
BIN_DIR = join(sys.prefix, 'Scripts' if on_Win else 'bin')


def get_python():
    if on_Win:
        return '"%s"' % sys.executable
    else:
        return sys.executable


def write_script(fpath, entry_pt, egg_name):
    print 'Creating script', fpath

    assert entry_pt.count(':') == 1
    module, func = entry_pt.strip().split(':')

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
            shutil.copyfile(join(BIN_DIR, 'egginst.exe'), exe)
            egg.files.append(exe)

            fname += '-script.py'

        fpath = join(BIN_DIR, fname)
        write_script(fpath, entry_pt, egg_name=basename(egg.fpath))
        egg.files.append(fpath)
