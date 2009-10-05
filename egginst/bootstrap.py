import sys
from os.path import isfile, join



def main(prefix=sys.prefix, verbose=False):
    """
    To bootstrap Enstaller into a Python environment, used the following
    code:

    sys.path.insert(0, '/path/to/Enstaller.egg')
    from egginst.bootstrap import main
    main()
    """
    import egginst

    # This is the path to the egg which we want to install.
    # Note that whoever calls this function has inserted the egg to the
    # from of sys.path
    egg_path = sys.path[0]

    print "Bootstrapping:", egg_path
    ei = egginst.EggInst(egg_path, prefix, verbose)
    ei.install()


def fix_easy_pth(pth):
    new_lines = []
    needs_rewrite = False
    for line in open(pth):
        line = line.strip()
        if 'enstaller' in line.lower():
            needs_rewrite = True
        else:
            new_lines.append(line)

    if needs_rewrite:
        fo = open(pth, 'w')
        for line in new_lines:
            fo.write(line + '\n')
        fo.close()
        print "Removed Enstaller entry from", pth


def remove_and_fix():
    # Remove and fix some files in site-packages
    from egginst.utils import rm_rf, rel_site_packages

    site_dir = join(sys.prefix, rel_site_packages)

    # Remove old Enstaller files which could cause problems
    for fn in ['Enstaller.pth', 'Enstaller.egg-link']:
        rm_rf(join(site_dir, fn))

    # If there an easy-install.pth in site-packages, remove and
    # occurrences of Enstaller from it.
    pth = join(site_dir, 'easy-install.pth')
    if isfile(pth):
        fix_easy_pth(pth)


def cli():
    """
    CLI (for executable egg)
    """
    from optparse import OptionParser
    from enstaller import __version__

    p = OptionParser(description="bootstraps Enstaller %(__version__)s into "
                                 "the Python environment" % locals())

    p.add_option("--prefix",
                 action="store",
                 default=sys.prefix,
                 help="install prefix, defaults to %default")

    p.add_option('-v', "--verbose", action="store_true")

    p.add_option('--version', action="store_true")

    opts, args = p.parse_args()

    if opts.version:
        print "Enstaller version:", __version__
        return

    main(opts.prefix, opts.verbose)

    remove_and_fix()
