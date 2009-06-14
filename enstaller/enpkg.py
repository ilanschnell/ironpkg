import os
import sys
import string
from os.path import basename, isdir, isfile, join

from enstaller.config import _get_config_path
from enstaller.indexed_repo import (IndexedRepo, Req, fetch, filename_dist,
                                    dist_as_req)
import egginst


def get_config():
    path = _get_config_path()
    res = {}
    if isfile(path):
        execfile(path, res)
    if 'repos' not in res:
        res['repos'] = []
    return res


config = get_config()


def fn_action(fn, action):
    print "%-56s %20s" % (fn, '[%s]' % action)


def main():
    from optparse import OptionParser

    p = OptionParser(
        usage="usage: %prog [options] Requirement",
        prog=basename(sys.argv[0]),
        description=("download and install eggs ..."))

    p.add_option('-n', "--dry-run",
                 action="store_true",
                 default=False)

    p.add_option('-l', "--list",
                 action="store_true",
                 default=False,
                 help="list all packages (with their versions) available "
                      "on the repo (chain), and exit")

    p.add_option('-v', "--verbose",
                 action="store_true",
                 default=False)

    p.add_option('-N', "--no-deps",
                 action="store_true",
                 default=False,
                 help="don't download (or install) dependencies")

    opts, args = p.parse_args()

    req = Req(' '.join(args))

    if opts.verbose:
        print "req = %r" % req

    ir = IndexedRepo(verbose=opts.verbose)

    for url in config['repos']:
        # add a repo from the config file to the chain
        ir.add_repo(url)

    if opts.list:
        names = set(spec['name'] for spec in ir.index.itervalues())
        for name in sorted(names, key=string.lower):
            r = Req(name)
            versions = set()
            for dist in ir.get_matches(r):
                if str(dist_as_req(dist)).startswith(str(req)):
                    versions.add(ir.index[dist]['version'])
            if versions:
                print "%-20s %s" % (name, ', '.join(sorted(versions)))
        return

    # This is a local directory, which is always first in the chain,
    # and the distributions are referenced by local:/<distname>
    if 'local_repo' in config:
        ir.local = config['local_repo']
    else:
        ir.local = join(sys.prefix, 'LOCAL-REPO')
    if not isdir(ir.local):
        os.mkdir(ir.local)
    # Add all distributions in the local repo to the index (without writing
    # any index files)
    ir.index_local_repo()

    if req.strictness == 0:
        p.error("Requirement missing")

    if opts.no_deps:
        dists = [ir.get_dist(req)]
    else:
        dists = ir.install_order(req)

    if opts.verbose:
        for d in dists:
            print '\t', filename_dist(d)

    for dist in dists:
        fn = filename_dist(dist)
        if opts.verbose:
            print 70 * '='
            print dist
        if isfile(join(ir.local, fn)):
            fn_action(fn, 'already exists')
        else:
            fn_action(fn, 'copy' if dist.startswith('file://') else 'download')
            if opts.dry_run:
                continue
            ir.fetch_dist(dist)

    print 77 * '='
    for dist in dists:
        fn = filename_dist(dist)
        egg_path = join(ir.local, fn)
        fn_action(fn, 'installing')
        if opts.dry_run:
            continue
        egginst.EggInst(egg_path, opts.verbose).install()


if __name__ == '__main__':
    main()
