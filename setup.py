from setuptools import setup, find_packages

setup(
    name = 'Enstaller',
    version = '0.0.1',
    description  = 'Enthought install tools',
    author       = 'Enthought, Inc',
    author_email = 'info@enthought.com',
    url          = 'http://code.enthought.com/ets',
    license      = '',
    zip_safe     = False,
    packages = find_packages(),
    include_package_data = True,
    install_requires = [
        "setuptools >= 0.6c6",
    ],
)
