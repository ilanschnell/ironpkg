The Enstaller (version 4) project in an install and managing tool
for egg-based Python distributions.

Enstaller consists of the three sub-packages:

egginst:
--------

egginst installs modules and packages directly into site-packages, i.e.
no .egg directories are created, hence there is no extra .pth-file which
results in a sorter python path and faster import times (which seems to
have the biggest advantage for namespace packages).  egginst knows about
the eggs the people from Enthought use.  It can install shared libraries,
change binary headers, etc., things which require special post install
scripts if (Enstaller) easy_install installs them.

enstaller:
----------

enstaller is the managing tool for egg-based installs, and the CLI is
called enpkg which calls out to egginst to do the actual install.
enpkg can access distributions from local and HTTP repositories, which
are pre-indexed.  The point of the index file, usually index-depend.bz2,
is that enpkg can download this file at the beginning of an install session
and resolve dependencies prior to downloading the actual files.

setuptools:
-----------

This is a patched version of setuptools with an additional easy_manage
command.  It is based on setuptools 0.6c9 with the following improvements:

 * added support for removing a package
 * added support for post-install and pre-uninstall scripts
 * improved dependency resolution with enpkg.
 * easy_install can now work through a proxy for both http and https urls.
 * setup.py develop also runs post-install scripts and --uninstall runs
   pre-uninstall scripts
 * easy_install and enpkg now prefer final releases of distributions over dev
   builds.


Remarks:
--------

 * Since the enpkg command is using egginst, and since the enpkg and egginst
   commands do not use setuptools code anymore (prior to version 4 they did),
   the setuptools fork will be removed from Enstaller in the future.
