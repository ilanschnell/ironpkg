# Author: Ilan Schnell <ischnell@enthought.com>

import os
import sys
import shutil
import zipfile
import ConfigParser
from os.path import abspath, basename, dirname, join, isdir, isfile

from utils import rmdir_er, dest_arc

on_Win = sys.platform.startswith('win')

if not on_Win:
    import links


DEBUG = 0


class EggInst(object):

    site_packages = join(dirname(os.__file__), 'site-packages')

    def __init__(self, fpath):
        self.fpath = fpath
        self.project = basename(fpath).split('-')[0]
        self.meta_dir = join(sys.prefix, 'eggmeta', self.project)
        self.files_txt = join(self.meta_dir, 'files.txt')
        self.files = []

    def install(self):
        if not isdir(self.meta_dir):
            os.makedirs(self.meta_dir)

        self.z = zipfile.ZipFile(self.fpath)
        self.arcnames = self.z.namelist()
        self.unpack()
        if not on_Win:
            self.mk_links()
            self.fix_object_files()
        self.z.close()
        self.entry_points()
        self.install_app()
        self.write_files()

    def entry_points(self):
        conf = ConfigParser.ConfigParser()
        conf.read(join(self.meta_dir, 'EGG-INFO/entry_points.txt'))
        if 'console_scripts' in conf.sections():
            import scripts
            scripts.create(self, conf)

    def write_files(self):
        fo = open(self.files_txt, 'wb')
        fo.write('\n'.join(self.files) + '\n')
        fo.close()

    def lines_from_arcname(self, arcname):
        if not arcname in self.arcnames:
            return
        for line in self.z.read(arcname).splitlines():
            line = line.strip()
            if line:
                yield line

    def mk_links(self):
        arcname = 'EGG-INFO/inst/files_to_install.txt'
        if arcname not in self.arcnames:
            return
        links.from_data(self.z.read(arcname))

    def rm_links(self):
        path = join(self.meta_dir, 'EGG-INFO', 'inst', 'files_to_install.txt')
        if not isfile(path):
            return
        links.from_data(open(path).read(), remove=True)

    def fix_object_files(self):
        from object_code import fix_files

        targets = [join(sys.prefix, 'lib')]
        for line in self.lines_from_arcname('EGG-INFO/inst/targets.dat'):
            targets.append(join(sys.prefix, line))
        if DEBUG:
            print 'Target directories:'
            for tgt in targets:
                print '    %s' % tgt
        fix_files(self.files, targets)

    def get_dst(self, name):
        if name.startswith('EGG-INFO/usr/'):
            return dest_arc(name)[1]

        if name.startswith('EGG-INFO'):
            dst_dir = self.meta_dir
        else:
            dst_dir = self.site_packages

        return join(dst_dir, *name.split('/'))

    def unpack(self):
        # Write the files
        for name in self.arcnames:
            if name.endswith('/'):
                # Some zip-files list dirs
                continue
            p = self.get_dst(name)
            self.files.append(p)
            if not isdir(dirname(p)):
                os.makedirs(dirname(p))
            fo = open(p, 'wb')
            fo.write(self.z.read(name))
            fo.close()
            if (name.startswith('EGG-INFO/usr/bin/') or
                name.endswith('.dylib') or '.so' in basename(name)):
                os.chmod(p, 0755)

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

    def remove(self):
        if not isdir(self.meta_dir):
            print "Can't find meta data for:", self.project
            return

        self.install_app(remove=True)

        if not on_Win:
            self.rm_links()

        # Read 'files.txt' from the meta_dir
        for line in open(self.files_txt):
            self.files.append(line.strip())

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
            if isfile(p):
                os.unlink(p)

        # Remove empty directories recursively
        for path in dirs:
            if isdir(path):
                rmdir_er(path)

        shutil.rmtree(self.meta_dir)


def main():
    from optparse import OptionParser

    usage = "usage: %prog [options] EGG [EGG ...]"

    description = """\
"""
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
