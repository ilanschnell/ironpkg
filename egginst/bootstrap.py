"""\
bootstraps Enstaller into a Python environment
"""
import sys
from os.path import isfile, join



def main(prefix=sys.prefix):
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

    print "Bootstraping:", egg_path
    ei = egginst.EggInst(egg_path, prefix=prefix)
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


def cli():
    """
    CLI (for executable egg)
    """
    from optparse import OptionParser
    from distutils.sysconfig import get_python_lib

    p = OptionParser(description=__doc__)

    p.add_option("--prefix",
                 action="store",
                 default=sys.prefix,
                 help="install prefix, defaults to %default")

    opts, args = p.parse_args()

    main(opts.prefix)

    # If there an easy-install.pth in site-packages, remove and
    # occurrences of Enstaller from it.
    pth = join(get_python_lib(), 'easy-install.pth')
    if isfile(pth):
        fix_easy_pth(pth)
