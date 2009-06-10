import os
import sys
import string
from os.path import basename, isdir, isfile, join
from optparse import OptionParser

from enstaller.indexed_repo import Platforms, IndexedRepo, Req, fetch
from enstaller.indexed_repo.utils import filename_dist
from egginst import egginst

from epd_repo.fetch import EGG_ROOT_URL


def fn_action(fn, action):
    print "%-56s %20s" % (fn, '[%s]' % action)


def main():
    platform_map = Platforms(EGG_ROOT_URL)
    if '-h' in sys.argv or '--help' in sys.argv:
        print "Platforms:"
        print platform_map.txt

    p = OptionParser(
        usage="usage: %prog [options] Requirement",
        prog=basename(sys.argv[0]),
        description=("fetches eggs from the EPD egg repository"))

    p.add_option('-i', "--install",
                 action="store_true",
                 default=False)

    p.add_option('-n', "--dry-run",
                 action="store_true",
                 default=False)

    p.add_option('-l', "--list",
                 action="store_true",
                 default=False,
                 help="list all packages (with thier versions) available")

    p.add_option('-p', "--platform-id",
                 action="store",
                 default=0,
                 help="platform ID for repo, see -l option")

    p.add_option('-v', "--verbose",
                 action="store_true",
                 default=False)

    p.add_option('-N', "--no-deps",
                 action="store_true",
                 default=False,
                 help="don't download dependencies")

    p.add_option('-t', "--test",
                 action="store_true",
                 default=False,
                 help="test the index for consistency and exit")

    opts, args = p.parse_args()

    if not opts.platform_id:
        if sys.platform == 'win32':
            opts.platform_id = 1
        elif sys.platform == 'darwin':
            opts.platform_id = 2

    subdir = platform_map.data[int(opts.platform_id)]['subdir']
    repo = EGG_ROOT_URL + subdir + '/'
    req_string = ' '.join(args)

    if opts.verbose:
        print "repo = %r" % repo
        print "req_string = %r" % req_string

    ir = IndexedRepo(verbose=opts.verbose)
    if opts.install:
        ir.local = join(sys.prefix, 'LOCAL-REPO')
    ir.add_repo(repo)

    if opts.list:
        names = set(spec['name'] for spec in ir.index.itervalues())
        for name in sorted(names, key=string.lower):
            req = Req(name)
            versions = set()
            for dist in ir.get_matches(req):
                versions.add(ir.index[dist]['version'])
            print "%-20s %s" % (name, ', '.join(sorted(versions)))
        return

    if opts.test:
        ir.test()
        return

    if opts.install and not isdir(ir.local):
        os.mkdir(ir.local)

    req = Req(req_string)
    if req.strictness == 0:
        p.error("Requirement missing")

    if opts.verbose:
        print "==================== %r ====================" % req

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
            fn_action(fn, 'download')
            if opts.dry_run:
                continue
            ir.fetch_dist(dist)

    if not opts.install:
        return

    print 77 * '='
    for dist in dists:
        fn = filename_dist(dist)
        egg_path = join(ir.local, fn)
        assert isfile(egg_path)
        fn_action(fn, 'installing')
        egginst(egg_path)


if __name__ == '__main__':
    main()
