import os
import re
import sys
import string
import subprocess
from os.path import basename, expanduser, isdir, isfile, join

import egginst

import config
from proxy.api import setup_proxy
from utils import cname_eggname, pprint_fn_action
from indexed_repo import filename_dist, Chain, Req



def configure(verbose=False):
    if config.get_path() is None:
        config.write()
    conf = config.read()

    if conf.has_key('LOCAL'):
        local = expanduser(conf['LOCAL'])
    else:
        local = join(sys.prefix, 'LOCAL-REPO')
    if not isdir(local):
        os.mkdir(local)

    repos = conf['IndexedRepos']

    if verbose:
        print "configuration:"
        print "\tlocal = %r" % local
        print "\trepos:"
        for repo in repos:
            print '\t    %r' % repo

    return local, repos


def call_egginst(args):
    fn = 'egginst'
    if sys.platform == 'win32':
        fn += '-script.py'
    path = join(sys.prefix, egginst.main.BIN_DIR_NAME, fn)
    subprocess.call([sys.executable, path] + args)


def check_write():
    path = join(sys.prefix, 'hello.txt')
    try:
        open(path, 'w').write('Hello World!\n')
    except:
        print "ERROR: Could not write simple file into:", sys.prefix
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


def remove_req(req, opts):
    for pkg in egginst.get_active():
        if req.name != cname_eggname(pkg):
            continue
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
    pprint_fn_action(pkg, 'removing')
    if not opts.dry_run:
        call_egginst(['--remove', pkg])


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
        prog=basename(sys.argv[0]),
        description=("download and install eggs ..."))

    p.add_option("--config",
                 action="store_true",
                 help="display the configuration and exit")

    p.add_option('-f', "--force",
                 action="store_true",
                 help="force download and install the main package "
                      "(not it's dependencies, see --forceall)")

    p.add_option("--forceall",
                 action="store_true",
                 help="force download and install of all packages "
                      "(i.e. including dependencies")

    p.add_option('-l', "--list",
                 action="store_true",
                 help="list the packages currently installed on the system")

    p.add_option('-n', "--dry-run",
                 action="store_true",
                 help="show what would have been downloaded/removed/installed")

    p.add_option('-N', "--no-deps",
                 action="store_true",
                 help="neither download nor install dependencies")

    p.add_option("--proxy",
                 action="store",
                 help="use a proxy for downloads")

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

    p.add_option('-v', "--verbose",
                 action="store_true")

    p.add_option('--version',
                 action="store_true")

    opts, args = p.parse_args()
    args_n = len(args)

    if args_n > 0 and (opts.list or opts.test or opts.config):
        p.error("Option takes no arguments")

    if opts.version:
        from enstaller import __version__
        print "Enstaller version:", __version__
        return

    if opts.config:
        cfg_path = config.get_path()
        print "config file:", cfg_path
        if cfg_path:
            configure(verbose=True)
        return

    if opts.list:
        egginst.print_active()
        return

    # Try to set up a proxy server, either from options or environment vars.
    # This makes urllib2 calls do the right thing.
    try:
        installed = setup_proxy(opts.proxy)
    except ValueError, e:
        print 'Proxy configuration error: %s' % e
        sys.exit(1)

    local, repos = configure(opts.verbose)
    c = Chain(repos, opts.verbose)

    if opts.search:
        search(c, opts.search)
        return

    if opts.test:
        c.test()
        return

    if args_n == 0:
        p.error("Requirement (that is, name and optional version) missing")
    if args_n > 2:
        p.error("A requirement is a name and an optional version")
    req = Req(' '.join(args))
    check_write()

    if opts.remove:
        remove_req(req, opts)
        return

    dists = c.install_order(req, recur=not opts.no_deps)

    if dists is None:
        print "No distribution found for requirement '%s'." % req
        versions = c.list_versions(req.name)
        if versions:
            print "Versions for package %r are: %s" % (req.name,
                                                       ', '.join(versions))
        return

    if opts.verbose:
        print "Distributions in install order:"
        for d in dists:
            print '\t', d

    # 'active' is the set of egg names which are currently active.
    active = set('%s.egg' % s for s in egginst.get_active())

    # These are the eggs which are being excluded from download and install
    exclude = set(active)
    if opts.force:
        exclude.discard(filename_dist(dists[-1]))
    elif opts.forceall:
        exclude = set()

    # Fetch distributions
    for dist, fn in iter_dists_excl(dists, exclude):
        if opts.dry_run:
            pprint_fn_action(fn, 'downloading')
            continue
        c.fetch_dist(dist, local, force=opts.force or opts.forceall)

    # Remove packages (in reverse install order)
    for dist in dists[::-1]:
        egg_name = filename_dist(dist)
        if egg_name in active:
            # if the distribution (which needs to be installed) is already
            # active don't remove it
            continue
        cname = cname_eggname(egg_name)
        for egg_a in active:
            if cname == cname_eggname(egg_a):
                pprint_fn_action(egg_a, 'removing')
                if not opts.dry_run:
                    call_egginst(['--remove', egg_a])

    # Install packages
    for dist, egg_name in iter_dists_excl(dists, exclude):
        pprint_fn_action(egg_name, 'installing')
        egg_path = join(local, egg_name)
        if not opts.dry_run:
            call_egginst([egg_path])


if __name__ == '__main__':
    main()
