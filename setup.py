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
ENSTALLERGUI = etsdep('enthought.enstaller.gui', '2.2.0b4', '2.3.0')
#ETS = etsdep('enthought.ets', '2.0.0b1')
ETSCONFIG = etsdep('enthought.etsconfig', '2.0.0b1')
TRAITS = etsdep('enthought.traits', '3.0.0b1')


setup(
    author = "Richard L. Ratzel",
    author_email = "info@enthought.com",
    maintainer = "Travis Oliphant",
    maintainer_email = "oliphant@enthought.com",
    dependency_links = [
        'http://code.enthought.com/enstaller/eggs/source',
        'http://code.enthought.com/enstaller/eggs/source/unstable',
        ],
    description = "The Enthought installer.  Enhances setuptools by adding " \
        "query options, support for post-install scripts, and much more.",
    entry_points = {
        # FIXME: The below should really only be inserted by the Enstaller
        # application building recipe.  Otherwise, builds of the ETS library
        # create a *broken* enstaller script!
        #"console_scripts" : [
        #    "enstaller = enthought.enstaller.launcher:launch",
        #    ],
        },
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
        #ETS,
        ETSCONFIG,
        TRAITS,
       ],
    license = "BSD",
    name = "enthought.enstaller",
    namespace_packages = [
        "enthought",
        "enthought.enstaller",
        ],
    packages = find_packages(),
    url = "http://code.enthought.com/enstaller",
    version = "2.2.0b4",
    zip_safe = False,
    )

