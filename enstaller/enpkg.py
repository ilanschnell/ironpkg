import os
import sys
import string
from os.path import basename, isdir, isfile, join

from config import get_configured_repos
from indexed_repo import chain, Req, filename_dist, dist_as_req
import egginst



def init_chain_from_config():
    for url in get_configured_repos():
        if url.startswith('local:'):
            # This is a local directory, which is always first in the chain,
            # and the distributions are referenced by local:/<distname>
            path = url[6:]
            if not isdir(path):
                os.mkdir(path)
            chain.local = path
        else:
            chain.add_repo(url)


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

    chain.verbose = opts.verbose
    init_chain_from_config()

    if opts.verbose:
        print "chain.local = %r" % chain.local
        for url in chain.chain:
            print '\turl = %r' % url

    if opts.list:
        names = set(spec['name'] for spec in chain.index.itervalues())
        for name in sorted(names, key=string.lower):
            r = Req(name)
            versions = set()
            for dist in chain.get_matches(r):
                if str(dist_as_req(dist)).startswith(str(req)):
                    versions.add(chain.index[dist]['version'])
            if versions:
                print "%-20s %s" % (name, ', '.join(sorted(versions)))
        return

    # Add all distributions in the local repo to the index (without writing
    # any index files)
    chain.index_all_local_files()

    if req.strictness == 0:
        p.error("Requirement missing")

    if opts.no_deps:
        dists = [chain.get_dist(req)]
    else:
        dists = chain.install_order(req)

    if opts.verbose:
        print "Distributions:"
        for d in dists:
            print '\t', filename_dist(d)

    for dist in dists:
        fn = filename_dist(dist)
        if opts.verbose:
            print 70 * '='
            print dist
        if isfile(join(chain.local, fn)):
            fn_action(fn, 'already exists')
        else:
            fn_action(fn, 'copy' if dist.startswith('file://') else 'download')
            if opts.dry_run:
                continue
            chain.fetch_dist(dist)

    print 77 * '='
    for dist in dists:
        fn = filename_dist(dist)
        egg_path = join(chain.local, fn)
        fn_action(fn, 'installing')
        if opts.dry_run:
            continue
        egginst.EggInst(egg_path, opts.verbose).install()


if __name__ == '__main__':
    main()
