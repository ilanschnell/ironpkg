# Author: Ilan Schnell <ischnell@enthought.com>
"""\
egginst is a simple tool for installing eggs into a Python environment.
"""

import os
import sys
import re
import shutil
import string
import zipfile
import ConfigParser
from os.path import abspath, basename, dirname, join, isdir, isfile, islink

from utils import on_win, bin_dir, rmdir_er, rm_rf, human_bytes
import scripts


# This is the directory which contains the EGG-INFO directories of all
# installed packages
EGG_INFO_DIR = join(sys.prefix, 'EGG-INFO')


class EggInst(object):

    site_packages = join(dirname(os.__file__), 'site-packages')

    def __init__(self, fpath, verbose=False):
        self.fpath = fpath
        self.project = basename(fpath).split('-')[0]
        self.meta_dir = join(EGG_INFO_DIR, self.project)
        self.files_txt = join(self.meta_dir, '__files__.txt')
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
        self.write_files()

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

    def write_files(self):
        fo = open(self.files_txt, 'w')
        fo.write('\n'.join(self.files) + '\n')
        fo.close()

    def read_files(self):
        for line in open(self.files_txt):
            self.files.append(line.strip())

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
            ('EGG-INFO/scripts/', True,       bin_dir),
            ('EGG-INFO/',         True,       self.meta_dir),
            ('',                  True,       self.site_packages),
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
        fpath = join(self.meta_dir, 'EGG-INFO', 'inst', 'appinst.dat')
        if not isfile(fpath):
            return

        try:
            import appinst
        except ImportError:
            print("Error: importing appinst failed.  Can't %sinstall "
                  "application (skipping)" % 'un' if remove else '')
            return

        if remove:
            appinst.uninstall_from_dat(fpath)
        else:
            appinst.install_from_dat(fpath)

    def run(self, fn):
        fpath = join(self.meta_dir, 'inst', fn)
        if not isfile(fpath):
            return
        from subprocess import call
        call([sys.executable, fpath], cwd=dirname(fpath))

    def remove(self):
        if not isdir(self.meta_dir):
            print "Error: Can't find meta data for:", self.project
            return

        self.run('pre_uninstall.py')
        self.install_app(remove=True)
        self.read_files()

        # After the loop, dirs will be a set of directories in which to
        # be removed (if empty, recursively).
        dirs = set()

        for p in self.files:
            ps = p.replace('\\', '/').split('/')
            if 'site-packages' in ps:
                spi = ps.index('site-packages')
                if len(ps) > spi + 2:
                    dirs.add(join(self.site_packages, ps[spi + 1]))
            elif not 'EGG-INFO' in ps:
                dirs.add(dirname(p))
            if islink(p) or isfile(p):
                os.unlink(p)

        # Remove empty directories recursively
        for path in dirs:
            if isdir(path):
                rmdir_er(path)

        shutil.rmtree(self.meta_dir)


def list_installed():
    """
    Returns a sorted list of all installed project names, i.e. the names
    of all directories in EGG_INFO_DIR.
    """
    res = [fn for fn in os.listdir(EGG_INFO_DIR)
           if isdir(join(EGG_INFO_DIR, fn))]
    res.sort(key=string.lower)
    return res


def main():
    from optparse import OptionParser

    usage = "usage: %prog [options] [EGG ...]"

    description = __doc__

    p = OptionParser(usage = usage,
                     description = description,
                     prog = basename(sys.argv[0]))

    p.add_option('-l', "--list",
                 action="store_true",
                 help="list installed package names and exit")

    p.add_option('-r', "--remove",
                 action="store_true",
                 help="remove packages, requires the egg or project names")

    p.add_option('-v', "--verbose", action="store_true")

    opts, args = p.parse_args()

    if opts.list:
        if args:
            p.error("--list takes no arguments")
        for name in list_installed():
            print name
        return

    for name in args:
        ei = EggInst(name, opts.verbose)
        if opts.remove:
            print "Removing:", name
            ei.remove()

        else: # default is always install
            print "Installing:", name
            ei.install()


if __name__ == '__main__':
    main()
