# Author: Ilan Schnell <ischnell@enthought.com>
"""\
egginst is a simple tool for installing eggs into a Python environment.
By default the eggs (provided as arguments) are installed.
"""

import os
import sys
import re
import shutil
import string
import zipfile
import ConfigParser
from os.path import abspath, basename, dirname, join, isdir, isfile, islink

from utils import (on_win, site_packages, rel_prefix, rmdir_er, rm_rf,
                   human_bytes)
import scripts


# This is the directory which contains the EGG-INFO directories of all
# installed packages
EGG_INFO_DIR = join(sys.prefix, 'EGG-INFO')

DEACTIVE_DIR = join(sys.prefix, 'DEACTIVE')


def projname(fn):
    return fn.split('-')[0]


class EggInst(object):

    def __init__(self, fpath, verbose=False):
        self.fpath = fpath
        self.name = projname(basename(fpath))
        self.meta_dir = join(EGG_INFO_DIR, self.name)
        self.meta_txt = join(self.meta_dir, '__egginst__.txt')
        self.files = []
        self.verbose = verbose

    def install(self):
        if not isdir(self.meta_dir):
            os.makedirs(self.meta_dir)

        self.z = zipfile.ZipFile(self.fpath)
        self.arcnames = self.z.namelist()

        self.extract()

        if on_win:
            scripts.create_proxies(self)

        else:
            import links
            import object_code

            if self.verbose:
                links.verbose = object_code.verbose = True

            links.create(self)
            object_code.fix_files(self)

        self.entry_points()
        self.z.close()
        scripts.fix_scripts(self)
        self.install_app()
        self.write_meta()

        self.run('post_install.py')

    def entry_points(self):
        lines = list(self.lines_from_arcname('EGG-INFO/entry_points.txt',
                                             ignore_empty=False))
        if lines == []:
            return

        path = join(self.meta_dir, '__entry_points__.txt')
        fo = open(path, 'w')
        fo.write('\n'.join(lines) + '\n')
        fo.close()

        conf = ConfigParser.ConfigParser()
        conf.read(path)
        if 'console_scripts' in conf.sections():
            if self.verbose:
                print 'creating console scripts'
                scripts.verbose = True
            scripts.create(self, conf)

    def write_meta(self):
        fo = open(self.meta_txt, 'w')
        fo.write('# egginst metadata\n')
        fo.write('egg_name = %r\n' % basename(self.fpath))
        fo.write('prefix = %r\n' % sys.prefix)
        fo.write('rel_files = [\n')
        fo.write('  %r,\n' % rel_prefix(self.meta_txt))
        for f in self.files:
            fo.write('  %r,\n' % rel_prefix(f))
        fo.write(']\n')
        fo.close()

    def read_meta(self):
        d = {}
        execfile(self.meta_txt, d)
        for name in ['egg_name', 'prefix', 'rel_files']:
            setattr(self, name, d[name])
        self.files = [join(self.prefix, f) for f in d['rel_files']]

    def lines_from_arcname(self, arcname,
                           ignore_empty=True,
                           ignore_comments=True):
        if not arcname in self.arcnames:
            return
        for line in self.z.read(arcname).splitlines():
            line = line.strip()
            if ignore_empty and line == '':
                continue
            if ignore_comments and line.startswith('#'):
                continue
            yield line

    def extract(self):
        cur = 0
        n = 0
        size = sum(self.z.getinfo(name).file_size
                   for name in self.arcnames)
        sys.stdout.write('%9s [' % human_bytes(size))
        for name in self.arcnames:
            n += self.z.getinfo(name).file_size
            rat = float(n) / size
            if rat * 64 >= cur:
                sys.stdout.write('.')
                sys.stdout.flush()
                cur += 1
            self.write_arcname(name)

        sys.stdout.write('.' * (65-cur) + ']\n')
        sys.stdout.flush()

    def get_dst(self, arcname):
        dispatch = [
            ('EGG-INFO/prefix/',  True,       sys.prefix),
            ('EGG-INFO/usr/',     not on_win, sys.prefix),
            ('EGG-INFO/scripts/', True,       scripts.bin_dir),
            ('EGG-INFO/',         True,       self.meta_dir),
            ('',                  True,       site_packages),
        ]
        for start, cond, dst_dir in dispatch:
            if arcname.startswith(start) and cond:
                return abspath(join(dst_dir, arcname[len(start):]))
        raise Exception("Didn't expect to get here")

    py_pat = re.compile(r'^(.+)\.py(c|o)?$')
    so_pat = re.compile(r'^lib.+\.so')
    py_obj = '.pyd' if on_win else '.so'
    def write_arcname(self, arcname):
        if arcname.endswith('/') or arcname.startswith('.unused'):
            return
        m = self.py_pat.match(arcname)
        if m and (m.group(1) + self.py_obj) in self.arcnames:
            # .py, .pyc, .pyo next to .so are not written
            return
        path = self.get_dst(arcname)
        dn, fn = os.path.split(path)
        self.files.append(path)
        if not isdir(dn):
            os.makedirs(dn)
        rm_rf(path, self.verbose)
        fo = open(path, 'wb')
        fo.write(self.z.read(arcname))
        fo.close()
        if (arcname.startswith('EGG-INFO/usr/bin/') or
                fn.endswith(('.dylib', '.pyd', '.so')) or
                (arcname.startswith('EGG-INFO/usr/lib/') and
                 self.so_pat.match(fn))):
            os.chmod(path, 0755)

    def install_app(self, remove=False):
        path = join(self.meta_dir, 'EGG-INFO', 'inst', 'appinst.dat')
        if not isfile(path):
            return

        try:
            import appinst
        except ImportError:
            print("Error: importing appinst failed.  Can't %sinstall "
                  "application (skipping)" % 'un' if remove else '')
            return

        if remove:
            appinst.uninstall_from_dat(path)
        else:
            appinst.install_from_dat(path)

    def run(self, fn):
        path = join(self.meta_dir, 'inst', fn)
        if not isfile(path):
            return
        from subprocess import call
        call([sys.executable, path], cwd=dirname(path))

    def rmdirs(self):
        """
        Remove empty directories for the files in self.files recursively
        """
        for path in set(dirname(p) for p in self.files):
            if isdir(path):
                rmdir_er(path)

    def remove(self):
        if not isdir(self.meta_dir):
            print "Error: Can't find meta data for:", self.name
            return

        self.read_meta()
        self.run('pre_uninstall.py')
        self.install_app(remove=True)

        for p in self.files:
            if islink(p) or isfile(p):
                os.unlink(p)
        self.rmdirs()
        rm_rf(self.meta_dir)

    def deactivate(self):
        """
        Deactivate a package, i.e. move the files belonging to the package
        into the special folder.
        """
        if not isdir(self.meta_dir):
            print "Error: Can't find meta data for:", self.name
            return
        self.read_meta()
        dn = self.egg_name[:-4]
        deact_dir = join(DEACTIVE_DIR, dn)
        if isdir(deact_dir):
            print "Error: Deactive data already exists for:", dn
            return
        os.makedirs(deact_dir)

        for rel_src in self.rel_files:
            src = join(self.prefix, rel_src)
            if islink(src) or isfile(src):
                dst = join(deact_dir, rel_src)
                dst_dir = dirname(dst)
                if not isdir(dst_dir):
                    os.makedirs(dst_dir)
                os.rename(src, dst)
        self.rmdirs()
        rm_rf(self.meta_dir)


def activate(dn):
    """
    Activate a package which was previously deactivated.  'dn' is the
    directory name inside the deactive folder, which is simply the egg
    name, without the .egg extension, of the egg which was used to install
    the package in the first place.
    """
    deact_dir = join(DEACTIVE_DIR, dn)
    if not isdir(deact_dir):
        print "Error: Can't find stored data for:", dn
        return
    for root, dirs, files in os.walk(deact_dir):
        for fn in files:
            src = join(root, fn)
            rel_src = src[len(deact_dir) + 1:]
            dst = join(sys.prefix, rel_src)
            dst_dir = dirname(dst)
            if not isdir(dst_dir):
                os.makedirs(dst_dir)
            rm_rf(dst)
            os.rename(src, dst)
    shutil.rmtree(deact_dir)


def get_active():
    """
    return a sroted list of all installed (active) packages
    """
    if not isdir(EGG_INFO_DIR):
        return []
    res = []
    for fn in os.listdir(EGG_INFO_DIR):
        meta_txt = join(EGG_INFO_DIR, fn, '__egginst__.txt')
        if isfile(meta_txt):
            d = {}
            execfile(meta_txt, d)
            res.append(d['egg_name'][:-4])
    res.sort(key=string.lower)
    return res


def get_deactive():
    """
    returns the set of all deactivated projects
    """
    if not isdir(DEACTIVE_DIR):
        return []
    res = [fn for fn in os.listdir(DEACTIVE_DIR)
           if isdir(join(DEACTIVE_DIR, fn))]
    res.sort(key=string.lower)
    return res


def print_list():
    fmt = '%-20s %-20s %s'
    print fmt % ('Project name', 'Version', 'Active')
    print 50 * '='

    active = get_active()
    deactive = get_deactive()
    names = set(projname(fn) for fn in active + deactive)
    output = []
    for name in sorted(names, key=string.lower):
        for lst, act in [(active, 'Yes'), (deactive, '')]:
            for fn in lst:
                if projname(fn) != name:
                    continue
                name, vers = fn.split('-', 1)
                output.append([name, vers, act])

    names = set()
    for row in output:
        if row[0] in names:
            row[0] = ''
        print fmt % tuple(row)
        names.add(row[0])


def main():
    from optparse import OptionParser

    usage = "usage: %prog [options] [ARGS ...]"

    description = __doc__

    p = OptionParser(usage = usage,
                     description = description,
                     prog = basename(sys.argv[0]))

    p.add_option('-a', "--activate",
                 action="store_true",
                 help="activate deactivated package(s)")

    p.add_option('-d', "--deactivate",
                 action="store_true",
                 help="deactives installed package(s)")

    p.add_option('-l', "--list",
                 action="store_true",
                 help="list packages, both active and deactive")

    p.add_option('-r', "--remove",
                 action="store_true",
                 help="remove package(s), requires the egg or project name(s)")

    p.add_option('-v', "--verbose", action="store_true")

    opts, args = p.parse_args()

    if opts.activate:
        for name in args:
            activate(name)
        return

    if opts.list:
        if args:
            p.error("--list takes no arguments")
        print_list()
        return

    for name in args:
        ei = EggInst(name, opts.verbose)
        if opts.remove:
            print "Removing:", name
            ei.remove()

        elif opts.deactivate:
            print "Deactivating:", name
            ei.deactivate()

        else: # default is always install
            print "Installing:", name
            ei.install()


if __name__ == '__main__':
    main()
