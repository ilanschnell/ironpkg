#!python
"""Bootstrap Enstaller installation

If you want to use Enstaller in your package's setup.py, just include this
file in the same directory with it, and add this to the top of your setup.py::

    from ez_setup import use_setuptools
    use_setuptools()

If you want to require a specific version of Enstaller, set a download
mirror, or use an alternate download directory, you can do so by supplying
the appropriate options to ``use_setuptools()``.

This file can also be run as a script to install or upgrade Enstaller.
"""


import os
import sys

try: from hashlib import md5
except ImportError: from md5 import md5


# Setup some global vars
DEFAULT_VERSION = "3.0.4"
DEFAULT_URL = "http://pypi.python.org/packages/%s/E/Enstaller/" % sys.version[:3]
md5_data = {
    'Enstaller-3.0.4-py2.4.egg': '6110e9daf82a72b990cf22cacd63db7c',
    'Enstaller-3.0.4-py2.5.egg': '90be6f931429c6bc76654d66b3c9cae1',
    'Enstaller-3.0.4-py2.6.egg': 'df2e41fab21ec0b8bbb7952e95b11a0d',
    'Enstaller-3.0.5-py2.4.egg': 'fdc7c833a3f8ff2f5c7642282767d65b',
    'Enstaller-3.0.5-py2.5.egg': '6a7f7ea7ae6fa49c42de3c10da2246c3',
    'Enstaller-3.0.5-py2.6.egg': '1c0f3a05a530fbe970a186c52a7a9443',
    'Enstaller-3.0.6-py2.4.egg': 'e86123bab51ac0006dabe5b2af0524f1',
    'Enstaller-3.0.6-py2.5.egg': '2932f69e2bf79eafec9c48e593ca480a',
    'Enstaller-3.0.6-py2.6.egg': '0d769f89eca4ada98eb9841ce215e2d1',
}


def _validate_md5(egg_name, data):
    if egg_name in md5_data:
        digest = md5(data).hexdigest()
        if digest != md5_data[egg_name]:
            print >>sys.stderr, (
                "md5 validation of %s failed!  (Possible download problem?)"
                % egg_name
            )
            sys.exit(2)
    return data


def use_setuptools(
    version=DEFAULT_VERSION, download_base=DEFAULT_URL, to_dir=os.curdir,
    download_delay=15
):
    """Automatically find/download Enstaller and make it available on sys.path

    `version` should be a valid Enstaller version number that is available
    as an egg for download under the `download_base` URL (which should end with
    a '/').  `to_dir` is the directory where Enstaller will be downloaded, if
    it is not already available.  If `download_delay` is specified, it should
    be the number of seconds that will be paused before initiating a download,
    should one be required.  If an older version of Enstaller is installed,
    this routine will print a message to ``sys.stderr`` and raise SystemExit in
    an attempt to abort the calling script.
    """
    was_imported = 'pkg_resources' in sys.modules or 'setuptools' in sys.modules
    def do_download():
        egg = download_setuptools(version, download_base, to_dir, download_delay)
        sys.path.insert(0, egg)
        import setuptools
        setuptools.bootstrap_install_from = egg
    try:
        import pkg_resources
    except ImportError:
        return do_download()
    try:
        pkg_resources.require("Enstaller>="+version)
        return
    except pkg_resources.VersionConflict, e:
        if was_imported:
            print >>sys.stderr, (
            "The required version of Enstaller (>=%s) is not available, and\n"
            "can't be installed while this script is running. Please install\n"
            " a more recent version first, using 'easy_install -U Enstaller'."
            "\n\n(Currently using %r)"
            ) % (version, e.args[0])
            sys.exit(2)
        else:
            del pkg_resources, sys.modules['pkg_resources']    # reload ok
            return do_download()
    except pkg_resources.DistributionNotFound:
        return do_download()


def download_setuptools(
    version=DEFAULT_VERSION, download_base=DEFAULT_URL, to_dir=os.curdir,
    delay = 15
):
    """Download setuptools from a specified location and return its filename

    `version` should be a valid setuptools version number that is available
    as an egg for download under the `download_base` URL (which should end
    with a '/'). `to_dir` is the directory where the egg will be downloaded.
    `delay` is the number of seconds to pause before an actual download attempt.
    """
    import urllib2, shutil
    egg_name = "Enstaller-%s-py%s.egg" % (version,sys.version[:3])
    url = download_base + egg_name
    saveto = os.path.join(to_dir, egg_name)
    src = dst = None
    if not os.path.exists(saveto):  # Avoid repeated downloads
        try:
            from distutils import log
            if delay:
                log.warn("""
---------------------------------------------------------------------------
This script requires Enstaller version %s to run (even to display
help).  I will attempt to download it for you (from
%s), but
you may need to enable firewall access for this script first.
I will start the download in %d seconds.

(Note: if this machine does not have network access, please obtain the file

   %s

and place it in this directory before rerunning this script.)
---------------------------------------------------------------------------""",
                    version, download_base, delay, url
                )
                from time import sleep
                sleep(delay)
            log.warn("Downloading %s", url)
            src = urllib2.urlopen(url)
            # Read/write all in one block, so we don't create a corrupt file
            # if the download is interrupted.
            data = _validate_md5(egg_name, src.read())
            dst = open(saveto,"wb")
            dst.write(data)
        finally:
            if src: src.close()
            if dst: dst.close()
    return os.path.realpath(saveto)


def main(argv, version=DEFAULT_VERSION):
    """Install or upgrade Enstaller"""
    try:
        import setuptools
    except ImportError:
        egg = None
        try:
            egg = download_setuptools(version, delay=0)
            sys.path.insert(0,egg)
            from setuptools.command.easy_install import main
            return main(list(argv)+[egg])   # we're done here
        finally:
            if egg and os.path.exists(egg):
                os.unlink(egg)
    else:
        res = setuptools.__version__.split('-')
        if len(res) < 2 or res[1][0] != 's':
            print >>sys.stderr, (
            "You have an obsolete version of setuptools installed.  Please\n"
            "remove it from your system entirely before running this script."
            )
            sys.exit(2)

    req = "Enstaller>="+version
    import pkg_resources
    try:
        pkg_resources.require(req)
    except pkg_resources.VersionConflict:
        try:
            from setuptools.command.easy_install import main
        except ImportError:
            from easy_install import main
        main(list(argv)+[download_setuptools(delay=0)])
        sys.exit(0) # try to force an exit
    else:
        if argv:
            from setuptools.command.easy_install import main
            main(argv)
        else:
            print "Enstaller version %s or greater has been installed." % version
            print '(Run "ez_enstaller.py -U Enstaller" to reinstall or upgrade.)'


def update_md5(filenames):
    """Update our built-in md5 registry"""

    import re

    for name in filenames:
        base = os.path.basename(name)
        f = open(name,'rb')
        md5_data[base] = md5(f.read()).hexdigest()
        f.close()

    data = ["    %r: %r,\n" % it for it in md5_data.items()]
    data.sort()
    repl = "".join(data)

    import inspect
    srcfile = inspect.getsourcefile(sys.modules[__name__])
    f = open(srcfile, 'rb')
    src = f.read()
    f.close()

    match = re.search("\nmd5_data = {\n([^}]+)}", src)
    if not match:
        print >>sys.stderr, "Internal error!"
        sys.exit(2)

    src = src[:match.start(1)] + repl + src[match.end(1):]
    f = open(srcfile, 'w')
    f.write(src)
    f.close()


if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--md5update':
        update_md5(sys.argv[2:])
    else:
        main(sys.argv[1:])

