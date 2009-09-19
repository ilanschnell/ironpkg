import os
import re
import sys
import string
from os.path import basename, expanduser, isdir, isfile, join

import egginst

import config
from utils import canonical
from indexed_repo import filename_dist, Chain, Req
from enstaller.utils import cname_eggname, pprint_fn_action, comparable_version



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


def search(repos, rx="?"):
    """
    Print the distributions available in a repo, i.e. a "virtual" repo made
    of a chain of (indexed) repos.
    """
    if rx != '?':
        pat = re.compile(rx, re.I)

    print "Packages available on:"
    for repo in repos:
        print '\t' + repo
    print

    fmt = "%-20s %s"
    print fmt % ('Project name', 'Versions')
    print 40 * '-'

    c = Chain(repos=repos)
    names = set(spec['name'] for spec in c.index.itervalues())
    for name in sorted(names, key=string.lower):
        if rx == '?' or pat.search(name):
            versions = c.list_versions(name)
            if versions:
                print fmt % (name, ', '.join(versions))


def remove_req(req, verbose=False):
    for pkg in egginst.get_active():
        if req.name != cname_eggname(pkg):
            continue
        if req.versions:
            v_a, b_a = pkg.split('-')[1:3]
            if req.versions[0] not in [v_a, '%s-%s' % (v_a, b_a)]:
                print("%s is installed cannot remove version %s." %
                      (pkg, req.versions[0]))
                return
        break
    else:
        print "Package %r does not seem to be installed." % req.name
        return
    pprint_fn_action(pkg, 'removing')
    egginst.EggInst(pkg, verbose).remove()


def main():
    from optparse import OptionParser

    p = OptionParser(
        usage="usage: %prog [options] [name] [version]",
        prog=basename(sys.argv[0]),
        description=("download and install eggs ..."))

    p.add_option("--config",
                 action="store_true",
                 default=False,
                 help="display the configuration and exit")

    p.add_option('-f', "--force",
                 action="store_true",
                 default=False,
                 help="force download and install")

    p.add_option('-l', "--list",
                 action="store_true",
                 default=False,
                 help="list the packages currently installed on the system")

    p.add_option('-N', "--no-deps",
                 action="store_true",
                 default=False,
                 help="don't download (or install) dependencies")

    p.add_option("--remove",
                 action="store_true",
                 default=False,
                 help="remove a package")

    p.add_option('-s', "--search",
                 action="store",
                 default=None,
                 help="search the index in the repo (chain) of packages "
                      "and display versions available.  Type '-s ?' to "
                      "display available versions for all packages.",
                 metavar='STR')

    p.add_option("--test",
                 action="store_true",
                 default=False,
                 help="perform some internal tests (for development only)")

    p.add_option('-v', "--verbose",
                 action="store_true",
                 default=False)

    p.add_option('--version',
                 action="store_true",
                 default=False)

    opts, args = p.parse_args()
    args_n = len(args)

    if args_n > 0 and (opts.list or opts.config):
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

    local, repos = configure(opts.verbose)

    if opts.search:
        search(repos, opts.search)
        return

    if opts.test:
        c = Chain(local, repos, opts.verbose)
        c.test()
        return

    check_write()

    if args_n == 0:
        p.error("Requirement (that is, name and optional version) missing")
    if args_n > 2:
        p.error("A requirement is a name and an optional version")
    req = Req(' '.join(args))

    if opts.remove:
        remove_req(req, opts.verbose)
        return

    # 'active' is a list of the egg names which are currently active.
    active = ['%s.egg' % s for s in egginst.get_active()]

    c = Chain(None, repos, opts.verbose)

    dists = c.install_order(req, recur=not opts.no_deps)

    if dists is None:
        print "No distribution found."
        versions = c.list_versions(req.name)
        if versions:
            print "Versions for package %r are: %s" % (req.name,
                                                       ', '.join(versions))
        return

    if opts.verbose:
        print "Distributions in install order:"
        for d in dists:
            print '\t', d

    # Fetch the distributions
    fetch_exclude = [] if opts.force else active
    c.local = local
    for dist in dists:
        if filename_dist(dist) in fetch_exclude:
            continue
        if opts.verbose:
            print 70 * '='
            print 'fetching: %r' % dist
        c.fetch_dist(dist, force=opts.force)

    remove = []
    for dist in dists:
        egg_name = filename_dist(dist)
        if egg_name in active:
            continue
        cname = cname_eggname(egg_name)
        for egg_a in active:
            if cname == cname_eggname(egg_a):
                remove.append(egg_a)

    install = []
    for dist in dists:
        egg_name = filename_dist(dist)
        if egg_name not in active:
            install.append(egg_name)

    if opts.verbose:
        print "These packages will be removed:"
        for egg_r in remove:
            print '\t' + egg_r[:-4]
        print
        print "These packages will be installed:"
        for egg_i in install:
            print '\t' + egg_i[:-4]
        print

    print 77 * '='
    for egg_r in remove:
        pprint_fn_action(egg_r, 'removing')
        egginst.EggInst(egg_r, opts.verbose).remove()

    for dist in dists:
        egg_name = filename_dist(dist)
        if opts.force or egg_name in install:
            pprint_fn_action(egg_name, 'installing')
            egg_path = join(local, egg_name)
            egginst.EggInst(egg_path, opts.verbose).install()
        else:
            pprint_fn_action(egg_name, 'already active')
            if egg_name not in active:
                print "Hmm, %s not active" % egg_name


if __name__ == '__main__':
    main()
