The Enstaller (version 4) project in an install and managing tool
for egg-based Python distributions.

Enstaller consists of the sub-packages:


enstaller:
----------

enstaller is a managing tool for egginst-based installs, and the CLI is
called enpkg which calls out to egginst to do the actual install.
enpkg can access distributions from local and HTTP repositories, which
are pre-indexed.  The point of the index file, usually index-depend.bz2,
is that enpkg can download this file at the beginning of an install session
and resolve dependencies prior to downloading the actual files.


egginst:
--------

egginst is the underlying tool for installing and uninstalling eggs.
The tool is brain dead in the sense that it does not care if the eggs
it installs are for the correct platform, it's dependencies got installed,
another package needs to be uninstalled prior to the install, and so on.
Those tasks are responsibilities of a package manager, and are outside
the scope of egginst.

egginst installs modules and packages directly into site-packages, i.e.
no .egg directories are created, hence there is no extra .pth-file which
results in a sorter python path and faster import times (which seems to
have the biggest advantage for namespace packages).  egginst knows about
the eggs the people from Enthought use.  It can install shared libraries,
change binary headers, etc., things which require special post install
scripts if (Enstaller) easy_install installs them.
