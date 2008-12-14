The Enstaller project is a replacement for setuptools that builds on
top of it and adds significant features.

It is based on setuptools 0.6c9

It starts from the setuptools source and adds the enstaller entry
point as well as specific improvements.

Improvements added:
-------------------

 * added support for removing a package
 * added support for post-install and pre-uninstall scripts
 * improved dependency resolution with enpkg.
 * easy_install can now work through a proxy for both http and https urls.
 * setup.py develop also runs post-install scripts and --uninstall runs
   pre-uninstall scripts
 * easy_install and enpkg now prefer final releases of distributions over dev
   builds.

Installation:
-------------

 * Remove setuptools from your system.
 * If your are not on a Windows platform, execute the egg:
   ``./Enstaller-3.0.4-py2.5.egg``
 * If you are on Windows, download the installation script for Enstaller:
   `ez_enstaller.py <http://code.enthought.com/src/ez_enstaller.py>`_
   and then un the script at a command prompt: ``python ez_enstaller.py``
 * Once the script completes, you will have the scripts
   enpkg and easy_install installed on your system.

To ensure that you are running Enstaller's easy_install, type at the
command prompt: ``easy_install --version``
This will print the Enstaller version number.
There is also an option ``-debug`` which gives various information about the
install location.

Remarks:
--------

 * While setuptools 0.6c9 still supports Python 2.3, Enstaller only
   supports Python 2.4 and higher (except 3.X).  Since much of the code is
   setuptools code old setuptools features may still work with Python 2.3,
   but added features may not.  No attempts are being made to maintain
   compatibility with Python 2.3.
