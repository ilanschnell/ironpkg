# Author: Ilan Schnell <ischnell@enthought.com>
"""\
egginst is a simple tool for installing eggs into a Python environment.
"""

import os
import sys
import shutil
import zipfile
import ConfigParser
from os.path import abspath, basename, dirname, join, isdir, isfile, islink

from utils import rmdir_er, on_win, bin_dir
import scripts


class EggInst(object):

    site_packages = join(dirname(os.__file__), 'site-packages')

    def __init__(self, fpath):
        self.fpath = fpath
        self.project = basename(fpath).split('-')[0]
        self.meta_dir = join(sys.prefix, 'eggmeta', self.project)
        self.files_txt = join(self.meta_dir, '__files__.txt')
        self.files = []

    def install(self):
        if not isdir(self.meta_dir):
            os.makedirs(self.meta_dir)

        self.z = zipfile.ZipFile(self.fpath)
        self.arcnames = self.z.namelist()
        for arcname in self.arcnames:
            self.write_arcname(arcname)

        if on_win:
            scripts.create_proxies(self)

        else:
            import links
            links.create(self)

            import object_code
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
            print 'creating console scripts'
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
        raise Exception("Hmm, didn't expect to get here")

    def write_arcname(self, arcname):
        if arcname.endswith('/') or arcname.startswith('.unused'):
            return
        path = self.get_dst(arcname)
        dn, fn = os.path.split(path)
        self.files.append(path)
        if not isdir(dn):
            os.makedirs(dn)
        fo = open(path, 'wb')
        fo.write(self.z.read(arcname))
        fo.close()
        if (arcname.startswith('EGG-INFO/usr/bin/') or
                fn.endswith(('.dylib', '.pyd')) or '.so' in fn):
            os.chmod(path, 0755)

    def install_app(self, remove=False):
        fpath = join(self.meta_dir, 'EGG-INFO', 'inst', 'appinst.dat')
        if not isfile(fpath):
            return

        try:
            import appinst
        except ImportError:
            print("Warning: importing appinst failed.  Can't %sinstall "
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
            print "Can't find meta data for:", self.project
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


def main():
    from optparse import OptionParser

    usage = "usage: %prog [options] EGG [EGG ...]"

    description = __doc__

    parser = OptionParser(usage = usage,
                          description = description,
                          prog = basename(sys.argv[0]))

    parser.add_option(
        "-r", "--remove",
        action = "store_true",
        help   = "Removing (requires the EGG filenames which were used "
                 "during the install)")

    opts, args = parser.parse_args()

    if len(args) < 1:
        parser.error("EGGs missing")

    for fpath in args:
        ei = EggInst(fpath)
        if opts.remove:
            print "Removing:", fpath
            ei.remove()
        else:
            print "Installing:", fpath
            ei.install()


if __name__ == '__main__':
    main()
