import sys
import os

from enstaller.indexed_repo import Chain, Req, filename_dist
import enstaller.indexed_repo.utils as utils



def filter_name(reqs, name):
    """
    from the requirements 'reqs', filter those for project 'name'
    """
    return set(r for r in reqs if r.name == name)


class Chain2(Chain):

    def add_reqs(self, reqs, req, level=1):

        for dist in self.get_matches(req):
            print 70 * '-'
            print filename_dist(dist)

            new_reqs = set()
            for r in self.reqs_dist(dist):
                # from all the reqs (we already have collected) filter the
                # ones with the project name of this requirement
                rs2 = filter_name(reqs, r.name)
                if rs2:
                    print '\t%r' % r
                    for r2 in rs2:
                        print '\t\t%r' % r2,
                        if r2.strictness > r.strictness:
                            new_reqs.add(r2)
                            print 'adding',
                        print
                else:
                    new_reqs.add(r)

            print 30 * '-'
            print 'new_reqs:', new_reqs
            print

            for r in new_reqs:
                if r in reqs:
                    continue
                reqs[r] = level
                self.add_reqs(reqs, r, level + 1)


    def get_reqs(self, req):
        """
        Returns a dictionary mapping all requirements found to the recursion
        level, i.e. how many nodes the requirement is located from the root.
        The root being level = 0, which is the requirement given by 'req' to
        this method itself, which is also included in the result.
        """
        # the root requirement (in the argument) itself
        reqs1 = {req: 0}

        # add all requirements for the root requirement
        self.add_reqs(reqs1, req)

        print "Requirements: (-level, strictness)"
        for r in sorted(reqs1):
            print '\t%-33r %3i %3i' % (r, -reqs1[r], r.strictness)

        reqs2 = set()
        for name in set(r.name for r in reqs1):
            # get all requirements for the name
            rs = []
            for r in filter_name(reqs1, name):
                rs.append(((-reqs1[r], r.strictness), r))

            rs.sort()
            if len(rs) > 1:
                print name
                print '\t', rs
                print '\t', rs[-1]
            reqs2.add(rs[-1])

        return [req for rank, req in reqs2]


    def install_order(self, req):
        """
        Return the list of distributions which need to be installed.
        The returned list is given in dependency order, i.e. the
        distributions can be installed in this order without any package
        being installed before its dependencies got installed.
        """
        # all requirements necessary for install
        reqs = self.get_reqs(req)

        # the corresponding distributions (sorted because the output of this
        # function is otherwise not deterministic)
        dists = sorted(self.get_dist(r) for r in reqs)

        # maps dist -> set of required (project) names
        rns = {}
        for dist in dists:
            rns[dist] = set(r.name for r in self.reqs_dist(dist))

        # As long as we have things missing, simply look for things which
        # can be added, i.e. all the requirements have been added already
        res = []
        names_inst = set()
        while len(res) < len(dists):
            n = len(res)
            for dist in dists:
                if dist in res:
                    continue
                # see if all required packages were added already
                if all(bool(n in names_inst) for n in rns[dist]):
                    res.append(dist)
                    names_inst.add(utils.canonical(self.index[dist]['name']))
                    assert len(names_inst) == len(res)
            if len(res) == n:
                # nothing was added
                print "WARNING: Loop in the dependency graph"
                break
        return res


# ----------------------------------------------------

from os.path import abspath, dirname
import string

c = Chain2(verbose=False)
for fn in ['repo1.txt', 'repo_pub.txt']:
    c.add_repo('file://%s/' % abspath(dirname(__file__)), fn)

#c.test()
#req = Req(' '.join(sys.argv[1:]))
req = Req('foo')

print '===== %r =====' % req
print filename_dist(c.get_dist(req))

rs = c.get_reqs(req)

if 0:
    print "Requirements:"
    for r in sorted(rs):
        print '\t%r' % r

print "Distributions:"
for d in c.install_order(req):
    print '\t', filename_dist(d)
