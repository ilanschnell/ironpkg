import os
import sys
import re
import shutil
from os.path import abspath, basename, exists, join, islink, isfile

from utils import on_win, bin_dir


def cp_exe(dst):
    shutil.copyfile(join(bin_dir, 'easy_install.exe'), dst)


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

    dst = join(bin_dir, dst_name)
    unlink(dst)
    cp_exe(dst)

    dst_script = dst[:-4] + '-script.py'
    unlink(dst_script)
    fo = open(join(bin_dir, dst_script), 'w')
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


def copy_to(src, dst_dir):
    dst = abspath(join(dst_dir, basename(src)))
    print "copying: %r" % src
    print "     to: %r" % dst
    unlink(dst)
    shutil.copyfile(src, dst)
    return dst


def create_proxies(egg):
    for line in egg.lines_from_arcname('EGG-INFO/inst/files_to_install.txt'):
        rel_name, action = line.replace('/', '\\').lstrip('\\').split()
        src = join(egg.meta_dir, rel_name[len('EGG-INFO/'):])
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
            exe_path = join(bin_dir, name + '.exe')
            unlink(exe_path)
            cp_exe(exe_path)
            egg.files.append(exe_path)

            fname += '-script.py'

        fpath = join(bin_dir, fname)
        write_script(fpath, entry_pt, egg_name=basename(egg.fpath))
        egg.files.append(fpath)


_hashbang_pat = re.compile(r'#!.+$', re.M)
def fix_script(path):
    if islink(path) or not isfile(path):
        return

    fi = open(path)
    data = fi.read()
    fi.close()

    m = _hashbang_pat.match(data)
    if not (m and 'python' in m.group().lower()):
        return

    new_data = _hashbang_pat.sub(
        ('#!"%s"' if on_win else '#!%s') % sys.executable,
        data, count=1)

    if new_data == data:
        return

    print "Updating: %r" % path
    fo = open(path, 'w')
    fo.write(new_data)
    fo.close()
    os.chmod(path, 0755)


def fix_scripts(egg):
    hashbang_pat = re.compile(r'#!(.+)$', re.M)
    for fpath in egg.files:
        if fpath.startswith(bin_dir):
            fix_script(fpath)
