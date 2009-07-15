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

    def select_new_reqs(self, reqs, dist):
        result = set()
        for r in self.reqs_dist(dist):
            # from all the reqs (we already have collected) filter the
            # ones with the same project name
            rs2 = filter_name(reqs, r.name)
            if rs2:
                # if there are requirements for an existing project name,
                # only add if it is more strict
                for r2 in rs2:
                    if r2.strictness > r.strictness:
                        result.add(r2)
            else:
                # otherwise, just add it, there is no requirement for this
                # project yet
                result.add(r)
        return result


    def add_reqs(self, reqs, req, level=1):
        for dist in self.get_matches(req):
            for r in self.select_new_reqs(reqs, dist):
                if r in reqs:
                    continue
                reqs[r] = (level, dist)
                self.add_reqs(reqs, r, level + 1)


    def get_reqs(self, req):
        """
        Returns a dictionary mapping all requirements found to the recursion
        level, i.e. how many nodes the requirement is located from the root.
        The root being level = 0, which is the requirement given by 'req' to
        this method itself, which is also included in the result.
        """
        # the root requirement (in the argument) itself
        reqs1 = {req: (0, 'local:ROOT')}

        # add all requirements for the root requirement
        self.add_reqs(reqs1, req)

        if self.verbose:
            print "Requirements: (-level, strictness)"
            for r in sorted(reqs1):
                print '\t%-33r %3i %3i' % (r, -reqs1[r][0], r.strictness)

        reqs2 = {}
        for name in set(r.name for r in reqs1):
            # get all requirements for the name
            rs = []
            for r in filter_name(reqs1, name):
                rs.append(((-reqs1[r][0], r.strictness), r, reqs1[r][1]))

            rs.sort()
            r, d = rs[-1][1:]
            reqs2[r] = d

        return reqs2


    def get_dist(self, req):
        """
        Return the distributions with the largest version and build number
        from the first repository which contains any matches.
        """
        lst = list(self.get_matches(req))
        lst.sort(key=self.get_version_build)
        if lst:
            return lst[-1]
        else:
            return None


    def install_order(self, req):
        """
        Return the list of distributions which need to be installed.
        The returned list is given in dependency order, i.e. the
        distributions can be installed in this order without any package
        being installed before its dependencies got installed.
        """
        # the distributions corresponding to the requirements must be sorted
        # because the output of this function is otherwise not deterministic
        dists = []
        for r, d in self.get_reqs(req).iteritems():
            dist = self.get_dist(r)
            if dist:
                dists.append(dist)
            else:
                print 'ERROR: No distribution found for: %r' % r
                print '       required by: %s' % d
                sys.exit(1)
        dists.sort()

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

c = Chain2(verbose=0)
for fn in ['repo1.txt', 'repo_pub.txt']:
    c.add_repo('file://%s/' % abspath(dirname(__file__)), fn)

#c.test()
#req = Req(' '.join(sys.argv[1:]))
req = Req('foo')

print '===== %r =====' % req
print filename_dist(c.get_dist(req))

rs = c.get_reqs(req)

if 1:
    print "Requirements:"
    for r in sorted(rs):
        print '\t%-40r %s' % (r, filename_dist(rs[r]))

if 1:
    print "Distributions:"
    for d in c.install_order(req):
        print '\t', filename_dist(d)
