import os
from setuptools import setup, find_packages


# Function to convert simple ETS project names and versions to a requirements
# spec that works for both development builds and stable builds.  Allows
# a caller to specify a max version, which is intended to work along with
# Enthought's standard versioning scheme -- see the following write up:
#    https://svn.enthought.com/enthought/wiki/EnthoughtVersionNumbers
def etsdep(p, min, max=None, literal=False):
    require = '%s >=%s.dev' % (p, min)
    if max is not None:
        if literal is False:
            require = '%s, <%s.a' % (require, max)
        else:
            require = '%s, <%s' % (require, max)
    return require


# Declare our ETS project dependencies.
ENSTALLERGUI = etsdep('EnstallerGUI', '2.2.0b4', '2.3.0')
ENTHOUGHTBASE = etsdep('EnthoughtBase', '3.0.0b1')
TRAITS_UI = etsdep('Traits[ui]', '3.0.0b1')


# Only setup a console script if the user is explicitly building the application
# instead of the library.
if len(os.environ.get('ENSTALLER_APP', '')) > 0:
    entry_points = {
        "console_scripts" : ["enstaller = enthought.enstaller.launcher:launch"],
        }
else:
    entry_points = {}


setup(
    author = "Enthought, Inc.",
    author_email = "info@enthought.com",
    dependency_links = [
        'http://code.enthought.com/enstaller/eggs/source',
        ],
    description = "A library of functionality used by Enthought installers.  " \
        "Enhances setuptools by adding query options, support for " \
        "post-install and pre-uninstall scripts, and much more.",
    entry_points = entry_points,
    extras_require = {
        "gui" : [
            ENSTALLERGUI,
            ],
        # All non-ets dependencies should be in this extra to ensure users can
        # decide whether to require them or not.
        'nonets': [
            ],
        },
    ext_modules = [],
    include_package_data = True,
    install_requires = [
        ENTHOUGHTBASE,
        TRAITS_UI,
       ],
    license = "BSD",
    name = "Enstaller",
    namespace_packages = [
        "enthought",
        "enthought.enstaller",
        ],
    packages = find_packages(),
    url = "http://code.enthought.com/enstaller",
    version = "2.2.0b4",
    zip_safe = False,
    )

