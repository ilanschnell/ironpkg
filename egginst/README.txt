
egginst
=======

egginst in an alternative egg (un)installer.  The main differences
to easy_install are:

  * modules and packages are installed directly into site-packages, i.e.
    no .egg directories are created, hence there is no extra .pth-file
    which results in a sorter python path and faster import times (which
    seems to have the biggest advantage for namespace packages).

  * egginst knows about the eggs the people from Enthought use.  It can
    install shared libraries, change binary headers, etc., things which
    require special post install scripts if (Enstaller) easy_install installs
    them.

  * The install is much more direct and kept simple.  This is probably the
    biggest difference to easy_install.


egginst
  - links
  - utils
  - object_code
  - scripts

depends
  - parsers
