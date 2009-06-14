"""
This is the API for egginst
===========================

More text here...


Egginst class
-------------

Is instantiated by an argument ARG (see below) and an optional verbose
keyword argument and has the following methods (for public use):

install():
    Installs the egg, provided by ARG, into the current Python environment

remove():
    Remove an installed package.  The ARG may be:
       * the full path of the egg which was used during the install
       * the egg name
       * or simply the project name

deactivate()
    Deactivate a package, i.e. move the files belonging to the package
    into the special folder.  ARG may be the same as for the remove method.


Functions:
----------

activate(name):
    Activate a package which was previously deactivated.  'name' is the
    directory name inside the deactive folder, which is simply the egg
    name, without the .egg extension, of the egg which was used to install
    the package in the first place.

get_active():
get_deactive():
    Returns a sorted list of the (de)activate packages.  Each element of
    the list is a 'name', see above.

print_list():
    write a list packages, both active and deactive, in a formatted manner
    to stdout.

bootstrap():
    see below

"""
from os.path import dirname

from main import EggInst, activate, get_active, get_deactive, print_list


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
