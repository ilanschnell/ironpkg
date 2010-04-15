egginst
=======

egginst in an egg (un)installer.  The main differences to easy_install are:

  * modules and packages are installed directly into site-packages, i.e.
    no .egg directories are created, hence there is no extra .pth-file
    which results in a sorter python path and faster import times (which
    seems to have the biggest advantage for large namespace packages,
    such as ETS).

  * egginst knows about the eggs the people from Enthought use.  It can
    install shared libraries, change binary headers, etc., things which
    would require special post install scripts if easy_install installs
    them.
