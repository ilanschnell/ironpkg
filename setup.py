from distutils.util import convert_path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

kwds = {} # Additional keyword arguments for setup

d = {}
execfile(convert_path('enstaller/__init__.py'), d)
kwds['version'] = d['__version__']

f = open('README.txt')
kwds['long_description'] = f.read()
f.close()


setup(
    name="IronPkg",
    author="Enthought, Inc.",
    author_email="info@enthought.com",
    url = "https://github.com/ilanschnell/ironpkg",
    license="BSD",
    description = "Install and managing tool for egg-based packages",
    packages = [
        'egginst',
        'enstaller',
        'enstaller/indexed_repo',
    ],
    entry_points = {
        "console_scripts": [
             "ironpkg = enstaller.main:main",
             "ironegg = egginst.main:main",
        ],
    },
    classifiers = [
        "License :: OSI Approved :: BSD License",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Software Distribution",
        "Topic :: System :: Systems Administration",
    ],
    **kwds
)
