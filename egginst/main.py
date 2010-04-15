# Author: Ilan Schnell <ischnell@enthought.com>
"""\
egginst is a simple tool for installing eggs into a Python environment.
By default the eggs (provided as arguments) are installed.
"""

import os
import sys
import re
import string
import zipfile
import ConfigParser
from os.path import abspath, basename, dirname, join, isdir, isfile

from egginst.utils import (on_win, bin_dir_name, rel_site_packages,
                           pprint_fn_action, rmdir_er, rm_rf, human_bytes)
import egginst.scripts as scripts


NS_PKG_PAT = re.compile(
    r'\s*__import__\([\'"]pkg_resources[\'"]\)\.declare_namespace'
    r'\(__name__\)\s*$')


def projname(fn):
    return fn.split('-')[0]


class EggInst(object):

    def __init__(self, fpath, prefix, verbose=False, noapp=False):
        self.fpath = fpath
        self.name = projname(basename(fpath))
        self.prefix = abspath(prefix)
        self.noapp = noapp

        # This is the directory which contains the EGG-INFO directories of all
        # installed packages
        self.meta_dir = join(self.prefix, 'EGG-INFO', self.name)
        self.meta_txt = join(self.meta_dir, '__egginst__.txt')

        self.bin_dir = join(self.prefix, bin_dir_name)
        self.site_packages = join(self.prefix, rel_site_packages)

        self.files = []
        self.verbose = verbose

    def rel_prefix(self, path):
        assert abspath(path).startswith(self.prefix)
        return path[len(self.prefix) + 1:]


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
        self.run('post_egginst.py')
        self.install_app()
        self.write_meta()


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
        if ('console_scripts' in conf.sections() or
            'gui_scripts' in conf.sections()):
            if self.verbose:
                print 'creating scripts'
                scripts.verbose = True
            scripts.create(self, conf)


    def write_meta(self):
        fo = open(self.meta_txt, 'w')
        fo.write('# egginst metadata\n')
        fo.write('egg_name = %r\n' % basename(self.fpath))
        fo.write('prefix = %r\n' % self.prefix)
        fo.write('installed_size = %i\n' % self.installed_size)
        fo.write('rel_files = [\n')
        fo.write('  %r,\n' % self.rel_prefix(self.meta_txt))
        for f in self.files:
            fo.write('  %r,\n' % self.rel_prefix(f))
        fo.write(']\n')
        fo.close()

    def read_meta(self):
        d = {}
        execfile(self.meta_txt, d)
        for name in ['egg_name', 'prefix', 'installed_size', 'rel_files']:
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
        cur = n = 0
        size = sum(self.z.getinfo(name).file_size for name in self.arcnames)
        sys.stdout.write('%9s [' % human_bytes(size))
        for name in self.arcnames:
            n += self.z.getinfo(name).file_size
            if size == 0:
                rat = 1
            else:
                rat = float(n) / size
            if rat * 64 >= cur:
                sys.stdout.write('.')
                sys.stdout.flush()
                cur += 1
            self.write_arcname(name)

        self.installed_size = size
        sys.stdout.write('.' * (65-cur) + ']\n')
        sys.stdout.flush()


    def get_dst(self, arcname):
        if arcname == 'EGG-INFO/PKG-INFO':
            name = self.name
            try:
                vers = basename(self.fpath).split('-')[1]
            except IndexError:
                vers = '0.0.0'
            major, minor = sys.version_info[:2]
            fn = "%(name)s-%(vers)s-py%(major)i.%(minor)i.egg-info" % locals()
            return join(self.site_packages, fn)

        for start, cond, dst_dir in [
            ('EGG-INFO/prefix/',  True,       self.prefix),
            ('EGG-INFO/usr/',     not on_win, self.prefix),
            ('EGG-INFO/scripts/', True,       self.bin_dir),
            ('EGG-INFO/',         True,       self.meta_dir),
            ('',                  True,       self.site_packages),
            ]:
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
        data = self.z.read(arcname)
        if fn in ['__init__.py', '__init__.pyc']:
            tmp = arcname.rstrip('c')
            if tmp in self.arcnames and NS_PKG_PAT.match(self.z.read(tmp)):
                if fn == '__init__.py':
                    data = ''
                if fn == '__init__.pyc':
                    return
        self.files.append(path)
        if not isdir(dn):
            os.makedirs(dn)
        rm_rf(path)
        fo = open(path, 'wb')
        fo.write(data)
        fo.close()
        if (arcname.startswith(('EGG-INFO/usr/bin/', 'EGG-INFO/scripts/')) or
                fn.endswith(('.dylib', '.pyd', '.so')) or
                (arcname.startswith('EGG-INFO/usr/lib/') and
                 self.so_pat.match(fn))):
            os.chmod(path, 0755)


    def install_app(self, remove=False):
        if self.noapp:
            return

        path = join(self.meta_dir, 'inst', 'appinst.dat')
        if not isfile(path):
            return

        try:
            import appinst
        except ImportError:
            return

        try:
            if remove:
                appinst.uninstall_from_dat(path)
            else:
                appinst.install_from_dat(path)
        except:
            print("Warning: An error occurred while %sinstalling application "
                  "item" % ('un' if remove else ''))


    def run(self, fn):
        path = join(self.meta_dir, fn)
        if not isfile(path):
            return
        from subprocess import call
        call([sys.executable, path, '--prefix', self.prefix],
             cwd=dirname(path))

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
        cur = n = 0
        nof = len(self.files) # number of files
        sys.stdout.write('%9s [' % human_bytes(self.installed_size))
        self.install_app(remove=True)
        self.run('pre_egguninst.py')

        for p in self.files:
            n += 1
            rat = float(n) / nof
            if rat * 64 >= cur:
                sys.stdout.write('.')
                sys.stdout.flush()
                cur += 1
            rm_rf(p)
            if p.endswith('.py') and isfile(p + 'c'):
                # remove the corresponding .pyc
                rm_rf(p + 'c')
        self.rmdirs()
        rm_rf(self.meta_dir)
        sys.stdout.write('.' * (65-cur) + ']\n')
        sys.stdout.flush()


def get_installed(prefix):
    """
    Generator returns a sorted list of all installed packages.
    Each element is the filename of the egg which was used to install the
    package.
    """
    egg_info_dir = join(prefix, 'EGG-INFO')
    if not isdir(egg_info_dir):
        return

    for fn in sorted(os.listdir(egg_info_dir), key=string.lower):
        meta_txt = join(egg_info_dir, fn, '__egginst__.txt')
        if not isfile(meta_txt):
            continue
        d = {}
        execfile(meta_txt, d)
        yield d['egg_name']


def print_installed(prefix, pat=None):
    fmt = '%-20s %s'
    print fmt % ('Project name', 'Version')
    print 40 * '='

    for fn in get_installed(prefix):
        if pat and not pat.search(fn):
            continue
        if '-' in fn:
            print fmt % tuple(fn[:-4].split('-', 1))
        else:
            print fn


def main():
    from optparse import OptionParser

    p = OptionParser(usage="usage: %prog [options] [EGGS ...]",
                     description=__doc__)

    p.add_option('-l', "--list",
                 action="store_true",
                 help="list all installed packages")

    p.add_option("--noapp",
                 action="store_true",
                 help="don't install/remove application menu items")

    p.add_option("--prefix",
                 action="store",
                 default=sys.prefix,
                 help="install prefix, defaults to %default")

    p.add_option('-r', "--remove",
                 action="store_true",
                 help="remove package(s), requires the egg or project name(s)")

    p.add_option('-v', "--verbose", action="store_true")
    p.add_option('-n', "--dry-run", action="store_true")
    p.add_option('--version', action="store_true")

    opts, args = p.parse_args()

    if opts.version:
        from enstaller import __version__
        print "Enstaller version:", __version__
        return

    prefix = abspath(opts.prefix)

    if opts.list:
        if args:
            p.error("the --list option takes no arguments")
        print_installed(prefix)
        return

    for path in args:
        ei = EggInst(path, prefix, opts.verbose, opts.noapp)
        fn = basename(path)
        if opts.remove:
            pprint_fn_action(fn, 'removing')
            if opts.dry_run:
                continue
            ei.remove()

        else: # default is always install
            pprint_fn_action(fn, 'installing')
            if opts.dry_run:
                continue
            ei.install()


if __name__ == '__main__':
    main()
