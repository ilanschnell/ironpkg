import os
from os.path import dirname, basename

from main import EGG_INFO_DIR, EggInst


def bootstrap(verbose=False):
    """
    To bootstrap Enstaller from within Python:

    sys.path.insert(0, <path to the Enstaller egg>)
    import egginst
    egginst.bootstrap()
    """
    egg_path = dirname(dirname(__file__))

    print "Bootstrapping:", egg_path
    EggInst(egg_path, verbose).install()


def install(egg_path, verbose=False):
    """
    Installs the egg.
    """
    print "Installing:", egg_path
    EggInst(egg_path, verbose).install()


def remove(name, verbose=False):
    """
    Remove the installed package.  'name' may be:
      * the full path of the egg which was used during the install
      * the egg name
      * or simply the project name
    """
    print "Removing:", name
    EggInst(name, verbose).remove()
