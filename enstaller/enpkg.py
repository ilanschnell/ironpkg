import os
import sys
import string
from os.path import basename, isdir, isfile, join

from config import get_configured_repos
from indexed_repo import (resolve, filename_dist, pprint_distname_action,
                          pprint_repo)
import egginst



def get_config():
    local = None
    repos = []
    for url in get_configured_repos():
        if not url.endswith('/'):
           url += '/'
        if not url.startswith(('local:', 'file://', 'http://')):
            print "Invalid repo in configuration:", url
            sys.exit(1)

        if url.startswith('local:'):
            # This is a local directory, which is always first in the chain,
            # and the distributions are referenced by local:<distname>
            local = url[6:]
        else:
            # These are indexed repos, url will start with file:// or http://
            repos.append(url)

    if local is None:
        local = join(sys.prefix, 'LOCAL-REPO')
        if not isdir(local):
            os.mkdir(local)

    return local, repos


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

    local, repos = get_config()

    if opts.verbose:
        print "configuration:"
        print "\tlocal = %r" % local
        print "\trepos:"
        for repo in repos:
            print '\t    %r' % repo

    req_string = ' '.join(args)
    if opts.list: # --list
        pprint_repo(local, repos, req_string)
        return

    if not args:
        p.error("Requirement missing")

    dists = resolve(req_string, local, repos,
                    recur=not opts.no_deps,
                    fetch=not opts.dry_run,
                    verbose=opts.verbose)

    if opts.dry_run:
        return

    print 77 * '='
    active = egginst.get_active()
    for dist in dists:
        egg_name = filename_dist(dist)
        assert egg_name.endswith('.egg')
        if egg_name[:-4] in active:
            pprint_distname_action(egg_name, 'already active')
            continue
        egg_path = join(local, egg_name)
        pprint_distname_action(egg_name, 'installing')
        if opts.dry_run:
            continue
        egginst.EggInst(egg_path, opts.verbose).install()


if __name__ == '__main__':
    main()
