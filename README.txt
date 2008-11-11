The Enstaller project is a replacement for setuptools that builds on
top of it and adds significant features.   

It is based on setuptools 0.6c9

It starts from the setuptools source and adds the enstaller entry
point as well as specific improvements.

Improvements added:

 * added post-install and pre-uninstall scripts
 * easy_install can now work through a proxy.
 * improved dependency resolution with enpkg.
 * ability to use .egg_info files located alongside the .egg file for
 getting dependency information
 * easy_install can work through a proxy
 * setup.py develop runs post-install scripts and --uninstall runs
 pre-uninstall scripts
 * easy_install prefers released versions of files.





