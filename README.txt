The Enstaller (version 4) project is a managing and install tool
for egg-based Python distributions.

Enstaller consists of the sub-packages enstaller and egginst:


enstaller:
----------

enstaller is a managing tool for egginst-based installs, and the CLI is
called enpkg which calls out to egginst to do the actual install.
enpkg can access distributions from local and HTTP repositories, which
are pre-indexed.  The point of the index file (index-depend.bz2) is that
enpkg can download this file at the beginning of an install session
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
change binary headers, etc., things which would require special post install
scripts if easy_install installs them.


The egg format:
---------------

The Enstaller egg format deals with two aspects: the actual install (egginst),
and the distribution management (enpkg).  As far as egginst is concerned,
the format is an extension of the setuptools egg format, i.e. all archive
files, except the ones starting with 'EGG-INFO/' are installed into the
site-packages directory.  In fact, since egginst a brain dead low-level tool,
it will even install an egg without an 'EGG-INFO' directory.  But more
importantly, egginst installs ordinary setuptools just fine.  Within the
'EGG-INFO/' namespace are special archives which egginst is looking for to
install files, as well as symbolic links, into locations other than
site-packages, and post install (and pre uninstall) scripts it can run.

As far as enpkg is concerned, eggs should contain a meta-data file with the
archive name 'EGG-INFO/spec/depend'.  The the index file (index-depend.bz2)
is essentially a compressed concatenation of the 'EGG-INFO/spec/depend' files
for all eggs in a directory/repository.


The metadata format:
--------------------

Build numbers are a way to differentiate eggs which have the have the
same name and version, but different dependencies.  The platform and
architecture dependencies of a distributions (or egg) is most easily
differentiated by putting them into different directories.  This leaves
us with the Python dependency and other egg dependencies to put into the
build number.  A dependencies specification data file is contained inside
the egg itself, that is in the archive ``EGG-INFO/spec/depend``, and the
md5sum and filesize is prepended to the data when the index-depend.bz2 is
created.


Installation:
-------------

The preferred and easiest way to install Enstaller from the executable egg,
e.i. the Enstaller egg contains a bash header, and on Unix system, you can
also download the egg and type::

   $ bash Enstaller-4.2.1-1.egg
   Bootstrapping: ...
   283 KB [.................................................................]

Once Enstaller is installed, it is possible to update itself.  Note that,
as Enstaller is the install tool for the Enthought Python Distribution (EPD),
all EPD installers already include Enstaller.
