import os
import sys
import string
from os.path import basename, expanduser, isdir, isfile, join

import egginst

import config
from indexed_repo import resolve, filename_dist, pprint_fn_action, pprint_repo



def configure(opts):
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

    if opts.verbose:
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


def main():
    from optparse import OptionParser

    p = OptionParser(
        usage="usage: %prog [options] Requirement",
        prog=basename(sys.argv[0]),
        description=("download and install eggs ..."))

    p.add_option('-n', "--dry-run",
                 action="store_true",
                 default=False)

    p.add_option('-f', "--force",
                 action="store_true",
                 default=False,
                 help="force download and install")

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

    p.add_option('--version',
                 action="store_true",
                 default=False)

    opts, args = p.parse_args()

    if opts.version:
        from enstaller import __version__
        print "Enstaller version:", __version__
        sys.exit(0)

    local, repos = configure(opts)

    req_string = ' '.join(args)
    if opts.list:
        pprint_repo(local, repos, req_string)
        return

    if not args:
        p.error("Requirement missing")

    check_write()

    # 'active' is a list of the egg names which are currently active.
    if opts.force:
        active = []
    else:
        active = ['%s.egg' % s for s in egginst.get_active()]

    dists = resolve(req_string, local, repos,
                    recur=not opts.no_deps,
                    fetch=not opts.dry_run,
                    fetch_force=opts.force,
                    fetch_exclude=active,
                    verbose=opts.verbose)

    if opts.dry_run:
        for d in dists:
            print d
        return

    print 77 * '='    
    for dist in dists:
        egg_name = filename_dist(dist)
        assert egg_name.endswith('.egg')
        if egg_name in active:
            pprint_fn_action(egg_name, 'already active')
            continue
        egg_path = join(local, egg_name)
        pprint_fn_action(egg_name, 'installing')
        if opts.dry_run:
            continue
        egginst.EggInst(egg_path, opts.verbose).install()


if __name__ == '__main__':
    main()
