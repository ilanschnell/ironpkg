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
    name="Enstaller",
    author="Enthought, Inc.",
    author_email="info@enthought.com",
    url = "http://code.enthought.com/projects/enstaller",
    license="BSD",
    description = "Install and managing tool for egg-based Python packages",
    packages = ['egginst', 'enstaller', 'enstaller/indexed_repo'],
    entry_points = {
        "console_scripts": [
             "enpkg = enstaller.enpkg:main",
             "egginst = egginst.main:main",
        ],
    },
    classifiers = [
        "License :: OSI Approved :: BSD License",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
    **kwds
)
