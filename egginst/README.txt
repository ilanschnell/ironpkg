
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

  * egginst does not aim to solve all problems at once.  All it tries to
    solve is installing and uninstalling eggs from a local file.  Problems
    such as, where the egg-file comes from, how it's dependencies are resolved,
    etc., are outside the scope of egginst.  However, this does not mean
    that other tools which are part of Enstaller won't address these problems
    (they should), but egginst does not.
