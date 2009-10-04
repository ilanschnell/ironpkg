from os.path import basename
from optparse import OptionParser

from ziputils import zip_select
from repack import repack_egg_with_meta

from enstaller.indexed_repo.dist_naming import is_valid_eggname


def main():
    p = OptionParser(
        usage="usage: %prog command [options] args",
        description="Tool for creating an indexed repository of eggs")

    p.add_option('-f', '--fetch',
        action="store_true",
        help="given a requirement, download the required egg (and it's "
        "dependencies), from the list of repositories given in the "
        ".enstaller4rc config file, into the CWD")

    p.add_option('-i', '--index',
        action="store_true",
        help="create index-depend.txt and index-depend.bz2 in the CWD "
        "from all eggs with valid names")

    p.add_option('-m', '--metadata',
        action="store_true",
        help="given indexed eggs, writes the metadata, i.e. the archive "
        "'EGG-INFO/spec/depend' to stdout.  Non-valid eggnames are ignored")

    p.add_option('-r', '--repack',
        action="store_true",
        help="given a setuptools egg (or many eggs), creates a new "
        "egg which contains additional metadata which then allows the egg "
        'to be added to an "indexed" repository (HTTP or local)')

    p.add_option('-v', "--verbose", action="store_true")

    opts, args = p.parse_args()

    if opts.fetch:
        pass # TODO

    if opts.index:
        pass # TODO

    if opts.metadata:
        for path in args:
            fn = basename(path)
            if is_valid_eggname(fn):
                print "==> %s <==" % fn
                print zip_select(path, 'EGG-INFO/spec/depend')
        return

    if opts.repack:
        for path in args:
            repack_egg_with_meta(path, opts.verbose)
        return


if __name__ == '__main__':
    main()
