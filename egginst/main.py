# Author: Ilan Schnell <ischnell@enthought.com>
"""\
ironpkg is a simple tool for installing and uninstalling eggs.  The tool
is brain dead in the sense that it does not care if the eggs it installs
are for the correct platform, it's dependencies got installed, another
package needs to be uninstalled prior to the install, and so on.  Those tasks
are responsibilities of a package manager, e.g. enpkg.  You just give it
eggs and it installs/uninstalls them.
"""
import os
import sys
import zipfile
import ConfigParser
from os.path import abspath, basename, dirname, join, isdir, isfile

from egginst.utils import pprint_fn_action, rmdir_er, rm_rf, human_bytes
from egginst import scripts


def name_version_fn(fn):
    """
    Given the filename of a package, returns a tuple(name, version).
    """
    if fn.endswith('.egg'):
        fn = fn[:-4]
    if '-' in fn:
        return tuple(fn.split('-', 1))
    else:
        return fn, ''


class EggInst(object):

    def __init__(self, fpath, verbose=False):
        self.fpath = fpath
        self.cname = name_version_fn(basename(fpath))[0].lower()

        # This is the directory which contains the EGG-INFO directories of all
        # installed packages
        self.meta_dir = join(sys.prefix, 'EGG-INFO', self.cname)
        self.meta_txt = join(self.meta_dir, '__egginst__.txt')
        self.bin_dir = sys.prefix
        self.site_packages = join(sys.prefix, r'Lib\site-packages')

        self.files = []
        self.verbose = verbose

    def rel_prefix(self, path):
        assert abspath(path).startswith(sys.prefix)
        return path[len(sys.prefix) + 1:]


    def install(self):
        if not isdir(self.meta_dir):
            os.makedirs(self.meta_dir)

        self.z = zipfile.ZipFile(self.fpath)
        self.arcnames = self.z.namelist()

        self.extract()

        scripts.create_proxies(self)

        self.entry_points()
        self.z.close()
        scripts.fix_scripts(self)
        self.run('post_egginst.py')
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
        fo.write('prefix = %r\n' % sys.prefix)
        fo.write('installed_size = %i\n' % self.installed_size)
        fo.write('rel_files = [\n')
        fo.write('  %r,\n' % self.rel_prefix(self.meta_txt))
        for f in self.files:
            fo.write('  %r,\n' % self.rel_prefix(f))
        fo.write(']\n')
        fo.close()

    def read_meta(self):
        d = {'installed_size': -1}
        execfile(self.meta_txt, d)
        for name in ['egg_name', 'prefix', 'installed_size', 'rel_files']:
            setattr(self, name, d[name])
        self.files = [join(sys.prefix, f) for f in d['rel_files']]


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
        for start, cond, dst_dir in [
            ('EGG-INFO/prefix/',  True,       sys.prefix),
            ('EGG-INFO/scripts/', True,       self.bin_dir),
            ('EGG-INFO/',         True,       self.meta_dir),
            ('',                  True,       self.site_packages),
            ]:
            if arcname.startswith(start) and cond:
                return abspath(join(dst_dir, arcname[len(start):]))
        raise Exception("Didn't expect to get here")

    def write_arcname(self, arcname):
        if arcname.endswith('/') or arcname.startswith('.unused'):
            return
        path = self.get_dst(arcname)
        dn, fn = os.path.split(path)
        data = self.z.read(arcname)

        self.files.append(path)
        if not isdir(dn):
            os.makedirs(dn)
        rm_rf(path)
        fo = open(path, 'wb')
        fo.write(data)
        fo.close()
        if arcname.startswith(('EGG-INFO/scripts/')) or fn.endswith('.pyd'):
            os.chmod(path, 0755)

    def run(self, fn):
        path = join(self.meta_dir, fn)
        if not isfile(path):
            return
        from subprocess import call
        call([sys.executable, path, '--prefix', sys.prefix],
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
            print "Error: Can't find meta data for:", self.cname
            return

        self.read_meta()
        cur = n = 0
        nof = len(self.files) # number of files
        sys.stdout.write('%9s [' % human_bytes(self.installed_size))
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


def get_installed():
    """
    Generator returns a sorted list of all installed packages.
    Each element is the filename of the egg which was used to install the
    package.
    """
    egg_info_dir = join(sys.prefix, 'EGG-INFO')
    if not isdir(egg_info_dir):
        return

    for fn in sorted(os.listdir(egg_info_dir)):
        meta_txt = join(egg_info_dir, fn, '__egginst__.txt')
        if not isfile(meta_txt):
            continue
        d = {}
        execfile(meta_txt, d)
        yield d['egg_name']


def print_installed():
    fmt = '%-20s %s'
    print fmt % ('Project name', 'Version')
    print 40 * '='
    for fn in get_installed():
        print fmt % name_version_fn(fn)


def main():
    from optparse import OptionParser

    p = OptionParser(usage="usage: %prog [options] [EGGS ...]",
                     description=__doc__)

    p.add_option('-l', "--list",
                 action="store_true",
                 help="list all installed packages")

    p.add_option('-r', "--remove",
                 action="store_true",
                 help="remove package(s), requires the egg or project name(s)")

    p.add_option('-v', "--verbose", action="store_true")
    p.add_option('-n', "--dry-run", action="store_true")
    p.add_option('--version', action="store_true")

    opts, args = p.parse_args()

    if opts.version:
        from enstaller import __version__
        print "IronPkg version:", __version__
        return

    if opts.list:
        if args:
            p.error("the --list option takes no arguments")
        print_installed()
        return

    for path in args:
        ei = EggInst(path, opts.verbose)
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
