import sys
from os.path import abspath, dirname

from enstaller.indexed_repo import Chain, Req, filename_dist



c = Chain(verbose=0)
c.add_repo('file://%s/' % abspath(dirname(__file__)), 'repo1.txt')
#c.add_repo('file:///home/ischnell/ETS_3.2.1/dist/')
c.add_repo('file://%s/' % abspath(dirname(__file__)), 'repo_pub.txt')
c.test()

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
