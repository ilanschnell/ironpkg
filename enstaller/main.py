# Author: Ilan Schnell <ischnell@enthought.com>
"""\
enstaller is a managing tool for egginst-based installs, and the CLI is
called enpkg which calls out to egginst to do the actual install.
enpkg can access distributions from local and HTTP repositories.
"""
import os
import re
import sys
import string
import time
from os.path import basename, dirname, getmtime, isdir, isfile, join
from optparse import OptionParser

import egginst
from egginst.utils import pprint_fn_action

import config
from utils import canonical, cname_fn, comparable_version
from indexed_repo import (Chain, Req, add_Reqs_to_spec, spec_as_req,
                          parse_data, dist_naming)


# global options variables
dry_run = None
verbose = None


def get_installed_info(cname):
    """
    Returns a dictionary with information about the package specified by the
    canonical name found in sys.prefix, or None if the package is not found.
    """
    egg_info_dir = join(sys.prefix, 'EGG-INFO')
    if not isdir(egg_info_dir):
        return None
    meta_txt = join(egg_info_dir, cname, '__egginst__.txt')
    if not isfile(meta_txt):
        return
    d = {}
    execfile(meta_txt, d)
    return dict(egg_name=d['egg_name'],
                mtime=time.ctime(getmtime(meta_txt)),
                meta_dir=dirname(meta_txt))


def egginst_remove(pkg):
    fn = basename(pkg)
    pprint_fn_action(fn, 'removing')
    if dry_run:
        return
    ei = egginst.EggInst(pkg)
    ei.remove()


def egginst_install(conf, dist):
    repo, fn = dist_naming.split_dist(dist)
    pkg_path = join(conf['local'], fn)

    pprint_fn_action(fn, 'installing')
    if dry_run:
        return

    ei = egginst.EggInst(pkg_path)
    ei.install()
    info = get_installed_info(cname_fn(fn))
    path = join(info['meta_dir'], '__enpkg__.txt')
    fo = open(path, 'w')
    fo.write("repo = %r\n" % repo)
    fo.close()


def print_installed_info(cname):
    info = get_installed_info(cname)
    if info is None:
        print "%s is not installed" % cname
    else:
        print "%(egg_name)s was installed on: %(mtime)s" % info


def info_option(c, cname):
    print "Canonic.:", cname
    print "In repositories:"
    req = Req(cname)
    for repo in c.repos:
        if c.get_matches_repo(req, repo):
            print '    %s' % repo
    print

    dist = c.get_dist(Req(cname))
    if dist:
        reqs = set(r.name for r in c.reqs_dist(dist))
        print "Requirements: %s" % ', '.join(sorted(reqs))

    print "Available versions: %s" % ', '.join(c.list_versions(cname))
    print_installed_info(cname)


repo_pat = re.compile(r'/repo/([^\s/]+/[^\s/]+)/')
def shorten_repo(repo):
    m = repo_pat.search(repo)
    if m:
        return m.group(1)
    else:
        return repo.replace('http://', '').replace('.enthought.com', '')


def print_installed(pat=None):
    fmt = '%-20s %-20s %s'
    print fmt % ('Project name', 'Version', 'Repository')
    print 60 * '='
    for fn in egginst.get_installed():
        if pat and not pat.search(fn[:-4]):
            continue
        lst = list(egginst.name_version_fn(fn))
        info = get_installed_info(cname_fn(fn))
        if info is None:
            lst.append('')
        else:
            path = join(info['meta_dir'], '__enpkg__.txt')
            if isfile(path):
                d = {}
                execfile(path, d)
                lst.append(shorten_repo(d['repo']))
            else:
                lst.append('')
        print fmt % tuple(lst)


def whats_new(c):
    fmt = '%-25s %-15s %s'
    print fmt % ('Name', 'installed', 'available')
    print 60* "="

    inst = set(egginst.get_installed())

    something_new = False
    for egg_name in inst:
        if not dist_naming.is_valid_eggname(egg_name):
            continue
        in_n, in_v, in_b = dist_naming.split_eggname(egg_name)
        dist = c.get_dist(Req(in_n))
        if dist is None:
            continue
        av_v = c.index[dist]['version']
        if (av_v != in_v and
                    comparable_version(av_v) > comparable_version(in_v)):
            print fmt % (in_n, in_v, av_v)
            something_new = True

    if not something_new:
        print "no new version of any installed package is available"


def search(c, pat=None):
    """
    Print the distributions available in a repo, i.e. a "virtual" repo made
    of a chain of (indexed) repos.
    """
    fmt = "%-25s %-15s %s"
    print fmt % ('Project name', 'Versions', 'Repository')
    print 55 * '-'

    names = set(spec['cname'] for spec in c.index.itervalues())
    for name in sorted(names, key=string.lower):
        if pat and not pat.search(name):
            continue
        versions = c.list_versions(name)
        if not versions:
            continue
        req = Req(name + ' ' + versions[-1])
        dist = c.get_dist(req)
        repo = dist_naming.repo_dist(dist)
        print fmt % (name, ', '.join(versions),  shorten_repo(repo))


def read_depend_files():
    """
    Returns a dictionary mapping canonical project names to the spec
    dictionaries of the installed packages.
    """
    egg_info_dir = join(sys.prefix, 'EGG-INFO')
    if not isdir(egg_info_dir):
        return {}
    res = {}
    for dn in os.listdir(egg_info_dir):
        path = join(egg_info_dir, dn, 'spec', 'depend')
        if isfile(path):
            fi = open(path)
            data = fi.read()
            fi.close()
            spec = parse_data(data)
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
    Tries remove a package from sys.prefix given a requirement object.
    This function is only used for the --remove option.
    """
    d = get_installed_info(req.name)
    if not d:
        print "Package %r does not seem to be installed." % req.name
        return
    pkg = d['egg_name'][:-4]
    if req.version:
        v_a, b_a = pkg.split('-')[1:3]
        if req.version != v_a or (req.build and req.build != int(b_a)):
            print("Version mismatch: %s is installed cannot remove %s." %
                  (pkg, req))
            return
    depend_warn([pkg], ignore_version=True)
    egginst_remove(pkg)


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
        sys.exit(1)

    if verbose:
        print "Distributions in install order:"
        for d in dists:
            print '    ', d
    return dists


def iter_dists_excl(dists, exclude_fn):
    """
    Iterates over all dists, excluding the ones whose filename is an element
    of exclude_fn.  Yields the distribution.
    """
    for dist in dists:
        fn = dist_naming.filename_dist(dist)
        if fn in exclude_fn:
            continue
        yield dist


def main():
    p = OptionParser(usage="usage: %prog [options] [name] [version]",
                     description=__doc__)

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

    p.add_option('-i', "--info",
                 action="store_true",
                 help="show information about a package")

    p.add_option('-l', "--list",
                 action="store_true",
                 help="list the packages currently installed on the system")

    p.add_option('-n', "--dry-run",
                 action="store_true",
                 help="show what would have been downloaded/removed/installed")

    p.add_option('-N', "--no-deps",
                 action="store_true",
                 help="neither download nor install dependencies")

    p.add_option("--remove",
                 action="store_true",
                 help="remove a package")

    p.add_option('-s', "--search",
                 action="store_true",
                 help="search the index in the repo (chain) of packages "
                      "and display versions available.")

    p.add_option('-v', "--verbose", action="store_true")

    p.add_option('--version', action="store_true")

    p.add_option("--whats-new",
                 action="store_true",
                 help="display to which installed packages updates are "
                      "available")

    opts, args = p.parse_args()

    if len(args) > 0 and opts.config:
        p.error("Option takes no arguments")

    if opts.force and opts.forceall:
        p.error("Options --force and --forceall exclude each ohter")

    pat = None
    if (opts.list or opts.search) and args:
        pat = re.compile(args[0], re.I)

    if opts.version:                              #  --version
        from enstaller import __version__
        print "IronPkg version:", __version__
        return

    if opts.config:                               #  --config
        config.print_config()
        return

    if config.get_path() is None:
        # create config file if it dosn't exist
        config.write()

    conf = config.read()                          #  conf

    global dry_run, version                       #  set globals
    dry_run = opts.dry_run
    version = opts.version

    if opts.list:                                 #  --list
        print_installed(pat)
        return

    c = Chain(conf['IndexedRepos'], verbose)      #  init chain

    if opts.search:                               #  --search
        search(c, pat)
        return

    if opts.info:                                 #  --info
        if len(args) != 1:
            p.error("Option requires one argument (name of package)")
        info_option(c, canonical(args[0]))
        return

    if opts.whats_new:                            # --whats-new
        if args:
            p.error("Option requires no arguments")
        whats_new(c)
        return

    if len(args) == 0:
        p.error("Requirement (name and optional version) missing")
    if len(args) > 2:
        p.error("A requirement is a name and an optional version")
    req = Req(' '.join(args))

    if opts.remove:                               #  --remove
        remove_req(req)
        return

    dists = get_dists(c, req,                     #  dists
                      recur=not opts.no_deps)

    # Warn the user about packages which depend on what will be updated
    depend_warn([dist_naming.filename_dist(d) for d in dists])

    # Packages which are installed currently
    inst = set(egginst.get_installed())

    # These are the packahes which are being excluded from being installed
    if opts.forceall:
        exclude = set()
    else:
        exclude = set(inst)
        if opts.force:
            exclude.discard(dist_naming.filename_dist(dists[-1]))

    # Fetch distributions
    if not isdir(conf['local']):
        os.makedirs(conf['local'])
    for dist in iter_dists_excl(dists, exclude):
        c.fetch_dist(dist, conf['local'],
                     check_md5=opts.force or opts.forceall,
                     dry_run=dry_run)

    # Remove packages (in reverse install order)
    for dist in dists[::-1]:
        fn = dist_naming.filename_dist(dist)
        if fn in inst:
            # if the distribution (which needs to be installed) is already
            # installed don't remove it
            continue
        cname = cname_fn(fn)
        for fn_inst in inst:
            if cname == cname_fn(fn_inst):
                egginst_remove(fn_inst)

    # Install packages
    installed_something = False
    for dist in iter_dists_excl(dists, exclude):
        installed_something = True
        egginst_install(conf, dist)

    if not installed_something:
        print "No update necessary, %s is up-to-date." % req
        print_installed_info(req.name)


if __name__ == '__main__':
    main()
