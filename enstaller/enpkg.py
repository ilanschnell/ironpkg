import os
import re
import sys
import string
import subprocess
from os.path import isdir, isfile, join

import egginst
from egginst.utils import bin_dir_name, rel_site_packages

import config
from proxy.api import setup_proxy
from utils import abs_expanduser, cname_fn
from indexed_repo import (filename_dist, Chain, Req, add_Reqs_to_spec,
                          spec_as_req, parse_data)


# global options
prefix = None
dry_run = None
verbose = None


def configure():
    if config.get_path() is None:
        config.write()
    conf = config.read()

    # prefix
    if conf.has_key('prefix'):
        conf['prefix'] = abs_expanduser(conf['prefix'])
    else:
        conf['prefix'] = sys.prefix

    # local
    if conf.has_key('local'):
        conf['local'] = abs_expanduser(conf['local'])
    else:
        conf['local'] = join(conf['prefix'], 'LOCAL-REPO')

    return conf


def print_config():
    print "sys.prefix:", sys.prefix
    cfg_path = config.get_path()
    print "config file:", cfg_path
    if cfg_path is None:
        return
    conf = configure()
    print
    print "config file setting:"
    print "\tprefix = %r" % conf['prefix']
    print "\tlocal = %r" % conf['local']
    print "\trepos:"
    for repo in conf['IndexedRepos']:
        print '\t    %r' % repo


def print_path():
    prefixes = [sys.prefix]
    if prefix != sys.prefix:
        prefixes.insert(0, prefix)
    print "Prefixes:"
    for p in prefixes:
        print '\t%s%s' % (p, ['', ' (sys)'][p == sys.prefix])
    print

    if sys.platform == 'win32':
        cmd = 'set'
    else:
        cmd = 'export'

    print "%s PATH=%s" % (cmd, os.pathsep.join(
                                 join(p, bin_dir_name) for p in prefixes))
    if prefix != sys.prefix:
        print "%s PYTHONPATH=%s" % (cmd, join(prefix, rel_site_packages))

    if sys.platform != 'win32':
        if sys.platform == 'darwin':
            name = 'DYLD_LIBRARY_PATH'
        else:
            name = 'LD_LIBRARY_PATH'
        print "%s %s=%s" % (cmd, name, os.pathsep.join(
                                 join(p, 'lib') for p in prefixes))


def list_option():
    print "sys.prefix:", sys.prefix
    egginst.print_installed(sys.prefix)
    if prefix != sys.prefix:
        print
        print "prefix:", prefix
        egginst.print_installed(prefix)


def call_egginst(pkg_path, remove=False):
    fn = 'egginst'
    if sys.platform == 'win32':
        fn += '-script.py'
    path = join(sys.prefix, bin_dir_name, fn)
    args = [sys.executable, path, '--prefix', prefix]
    if dry_run:
        args.append('--dry-run')
    if remove:
        args.append('--remove')
    args.append(pkg_path)
    if verbose:
        print 'CALL: %r' % args
    subprocess.call(args)


def check_write():
    path = join(prefix, 'hello.txt')
    try:
        open(path, 'w').write('Hello World!\n')
    except:
        print "ERROR: Could not write simple file into:", prefix
        sys.exit(1)
    finally:
        if isfile(path):
            os.unlink(path)


def search(c, rx="?"):
    """
    Print the distributions available in a repo, i.e. a "virtual" repo made
    of a chain of (indexed) repos.
    """
    if rx != '?':
        pat = re.compile(rx, re.I)

    fmt = "%-20s %s"
    print fmt % ('Project name', 'Versions')
    print 40 * '-'

    names = set(spec['name'] for spec in c.index.itervalues())
    for name in sorted(names, key=string.lower):
        if rx == '?' or pat.search(name):
            versions = c.list_versions(name)
            if versions:
                print fmt % (name, ', '.join(versions))


def read_depend_files():
    """
    Returns a dictionary mapping canonical project names to the spec
    dictionaries of the installed packages.
    """
    res = {}
    egg_info_dir = join(prefix, 'EGG-INFO')
    for name in os.listdir(egg_info_dir):
        path = join(egg_info_dir, name, 'spec', 'depend')
        if isfile(path):
            spec = parse_data(open(path).read())
            add_Reqs_to_spec(spec)
            res[spec['cname']] = spec
    return res


def depend_warn(pkgs, ignore_version=False):
    """
    Warns the user about packages to be changed (i.e. removed or updated),
    if other packages depend on the package.

    Warnings are printed when the required name of the package matches.
    The ignore_version option determines if a version comparison is also
    desired as well, which it is not for the --remove option, since when
    a package is removed it does not matter which version is required.
    Hence, in remove_req() this function is called with ignore_version=True.
    """
    names = {}
    for pkg in pkgs:
        names[cname_fn(pkg)] = pkg
    index = read_depend_files()
    for spec in index.itervalues():
        if spec['cname'] in names:
            continue
        for req in spec["Reqs"]:
            if req.name not in names:
                continue
            if (ignore_version or
                     (req.version and
                      req.version != names[req.name].split('-')[1])):
                print "Warning: %s depends on %s" % (spec_as_req(spec), req)


def remove_req(req):
    """
    Tries remove a package from prefix given a requirement object.
    This function is only used for the --remove option.
    """
    for fn in egginst.get_installed(prefix):
        if req.name != cname_fn(fn):
            continue
        pkg = fn[:-4]
        if req.version:
            v_a, b_a = pkg.split('-')[1:3]
            if req.version != v_a or (req.build and req.build != int(b_a)):
                print("Version mismatch: %s is installed cannot remove %s." %
                      (pkg, req))
                return
        break
    else:
        print "Package %r does not seem to be installed." % req.name
        return
    depend_warn([pkg], ignore_version=True)
    call_egginst(pkg, remove=True)


def get_dists(c, req, recur):
    """
    Resolves the requirement
    """
    dists = c.install_order(req, recur=recur)
    if dists is None:
        print "No distribution found for requirement '%s'." % req
        versions = c.list_versions(req.name)
        if versions:
            print "Versions for package %r are: %s" % (req.name,
                                                       ', '.join(versions))
        else:
            print # Temporary message until enpkg can handle PyPI
            print "You may want to run: easy_install %s" % req.name
        sys.exit(0)

    if verbose:
        print "Distributions in install order:"
        for d in dists:
            print '\t', d
    return dists


def iter_dists_excl(dists, exclude_fn):
    """
    Iterates over all dists, excluding the ones whose filename is an element
    of exclude_fn.  Yields both the distribution and filename.
    """
    for dist in dists:
        fn = filename_dist(dist)
        if fn in exclude_fn:
            continue
        yield dist, fn


def main():
    from optparse import OptionParser

    p = OptionParser(
        usage="usage: %prog [options] [name] [version]",
        description=("download and install eggs ..."))

    p.add_option("--config",
                 action="store_true",
                 help="display the configuration and exit")

    p.add_option('-f', "--force",
                 action="store_true",
                 help="force install the main package "
                      "(not it's dependencies, see --forceall)")

    p.add_option("--forceall",
                 action="store_true",
                 help="force install of all packages "
                      "(i.e. including dependencies)")

    p.add_option('-l', "--list",
                 action="store_true",
                 help="list the packages currently installed on the system")

    p.add_option('-n', "--dry-run",
                 action="store_true",
                 help="show what would have been downloaded/removed/installed")

    p.add_option('-N', "--no-deps",
                 action="store_true",
                 help="neither download nor install dependencies")

    p.add_option("--path",
                 action="store_true",
                 help="based on the configuration, display how to set the "
                      "PATH and PYTHONPATH environment variables")

    p.add_option("--prefix",
                 action="store",
                 help="install prefix (disregarding of any settings in "
                      "the config file)",
                 metavar='PATH')

    p.add_option("--sys-prefix",
                 action="store_true",
                 help="use sys.prefix as the install prefix")

    p.add_option("--proxy",
                 action="store",
                 help="use a proxy for downloads",
                 metavar='URL')

    p.add_option("--remove",
                 action="store_true",
                 help="remove a package")

    p.add_option('-s', "--search",
                 action="store",
                 help="search the index in the repo (chain) of packages "
                      "and display versions available.  Type '-s ?' to "
                      "display available versions for all packages.",
                 metavar='STR')

    p.add_option("--test",
                 action="store_true",
                 help="perform some internal tests (for development only)")

    p.add_option('-v', "--verbose", action="store_true")

    p.add_option('--version', action="store_true")

    opts, args = p.parse_args()

    if len(args) > 0 and (opts.list or opts.test or opts.config or opts.path):
        p.error("Option takes no arguments")

    if opts.prefix and opts.sys_prefix:
        p.error("Options --prefix and --sys-prefix exclude each ohter")

    if opts.force and opts.forceall:
        p.error("Options --force and --forceall exclude each ohter")

    if opts.version:                              #  --version
        from enstaller import __version__
        print "Enstaller version:", __version__
        return

    if opts.config:                               #  --config
        print_config()
        return

    conf = configure()                            #  conf

    global prefix, dry_run, version               # set globals
    if opts.sys_prefix:
        prefix = sys.prefix
    elif opts.prefix:
        prefix = opts.prefix
    else:
        prefix = conf['prefix']
    dry_run = opts.dry_run
    version = opts.version

    if opts.path:                                 #  --path
        print_path()
        return

    if opts.list:                                 #  --list
        list_option()
        return

    try:                                          # proxy server
        installed = setup_proxy(opts.proxy)
    except ValueError, e:
        print 'Proxy configuration error: %s' % e
        sys.exit(1)

    c = Chain(conf['IndexedRepos'], verbose)      # init chain

    if opts.search:                               # --search
        search(c, opts.search)
        return

    if opts.test:                                 # --test
        c.test()
        return

    if len(args) == 0:
        p.error("Requirement (name and optional version) missing")
    if len(args) > 2:
        p.error("A requirement is a name and an optional version")
    req = Req(' '.join(args))

    print "prefix:", prefix
    check_write()
    if opts.remove:                               # --remove
        remove_req(req)
        return

    dists = get_dists(c, req,                     # dists
                      recur=not opts.no_deps)

    # Warn the user about packages which depend on what will be updated
    depend_warn([filename_dist(d) for d in dists])

    # Packages which are installed currently
    sys_inst = set(egginst.get_installed(sys.prefix))
    if prefix == sys.prefix:
        prefix_inst = sys_inst
    else:
        prefix_inst = set(egginst.get_installed(prefix))
    all_inst = sys_inst | prefix_inst

    # These are the packahes which are being excluded from being installed
    if opts.forceall:
        exclude = set()
    else:
        exclude = all_inst
        if opts.force:
            exclude.discard(filename_dist(dists[-1]))

    # Fetch distributions
    if not isdir(conf['local']):
        os.makedirs(conf['local'])
    for dist, fn in iter_dists_excl(dists, exclude):
        c.fetch_dist(dist, conf['local'],
                     check_md5=opts.force or opts.forceall,
                     dry_run=dry_run)

    # Remove packages (in reverse install order)
    for dist in dists[::-1]:
        fn = filename_dist(dist)
        if fn in all_inst:
            # if the distribution (which needs to be installed) is already
            # installed don't remove it
            continue
        cname = cname_fn(fn)
        # Only remove packages installed in prefix
        for fn_inst in prefix_inst:
            if cname == cname_fn(fn_inst):
                call_egginst(fn_inst, remove=True)

    # Install packages
    for dist, fn in iter_dists_excl(dists, exclude):
        call_egginst(join(conf['local'], fn))


if __name__ == '__main__':
    main()
