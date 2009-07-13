import sys
import os

from enstaller.indexed_repo import Chain, Req, filename_dist
import enstaller.indexed_repo.utils as utils


class Chain2(Chain):

    def _add_reqs(self, reqs, req, level=1):
        for dist in self.get_matches(req):
            for r in self.reqs_dist(dist):
                if r in reqs:
                    # a loop in the dependency tree would cause infinite
                    # recursion, unless we skip here.
                    continue
                reqs[r] = level
                # recursion
                self._add_reqs(reqs, r, level + 1)

    def get_reqs(self, req):
        """
        Returns the set of requirements, which are necessary to install 'req'.
        For each required (project) name, only one requirement, i.e. the one
        with the highest strictness, is contained in the output.
        """       
        # first, get all requirements
        reqs = {}
        self._add_reqs(reqs, req)
        reqs[req] = 0

        return reqs

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


c = Chain2(verbose=False)
from os.path import abspath, dirname
for fn in ['repo1.txt', 'repo_pub.txt']:
    c.add_repo('file://%s/' % abspath(dirname(__file__)), fn)

#c.test()
#req = Req(' '.join(sys.argv[1:]))
req = Req('foo')

print '===== %r =====' % req
print filename_dist(c.get_dist(req))

print "Requirements: (strictness, level)"
for r, level in c.get_reqs(req).iteritems():
    print '\t%-33r  %i  %i' % (r, r.strictness, level)

print "Distributions:"
for d in c.install_order(req):
    print '\t', filename_dist(d)
