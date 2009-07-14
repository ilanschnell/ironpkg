import sys
import os

from enstaller.indexed_repo import Chain, Req, filename_dist
import enstaller.indexed_repo.utils as utils


class Chain2(Chain):

    def add_reqs(self, reqs, req, level=1):

        for dist in self.get_matches(req):
            for r in self.reqs_dist(dist):

                names = set(r.name for r in reqs)

                if r.name in names:
                    print '%-20s: %r' % (r.name, r)
                    for r2 in reqs:
                        if r2.name == r.name and r2 != r:
                            print '\t%r' % r2
                    print
                    continue

                if r in reqs:
                    # a loop in the dependency tree would cause infinite
                    # recursion, unless we skip here.
                    continue

                reqs[r] = level

                # recursion
                self.add_reqs(reqs, r, level + 1)


    def get_all_reqs(self, req):
        """
        Returns a dictionary mapping all requirements found to the recursion
        level, i.e. how many nodes the requirement is located from the root.
        The root being level = 0, which is the requirement given by 'req' to
        this method itself, which is also included in the result.
        """
        # the requirement (in the argument) itself
        result = {req: 0}

        # get all requirements
        self.add_reqs(result, req)

        return result


    def get_reqs(self, req):
        """

        """
        reqs = self.get_all_reqs(req)

        # the set of all required (project) names
        names = set(r.name for r in reqs)

        res = set()
        for name in names:
            # get all requirements for the name
            rs = [r for r in reqs if r.name == name]
            # add the requirement with greatest strictness
            rs.sort(key=lambda r: r.strictness)
            res.add(rs[-1])
        return res


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

print "Requirements: (strictness, level) -- all"
rs = c.get_all_reqs(req)
for r in sorted(rs.keys(), key=lambda r: r.name):
    print '\t%-33r  %i  %i' % (r, r.strictness, rs[r])

exit(0)

print "Requirements: (strictness)"
rs = c.get_reqs(req)
for r in sorted(rs, key=lambda r: r.name):
    print '\t%-33r  %i' % (r, r.strictness)

print "Distributions:"
for d in c.install_order(req):
    print '\t', filename_dist(d)
