import sys
import os

from enstaller.indexed_repo import Chain, Req, filename_dist


c = Chain(verbose=False)
c.add_repo('file://%s/' % os.getcwd(), 'repo1.txt')

req = Req(sys.argv[1])
print '===== %r =====' % req
print filename_dist(c.get_dist(req))

print "Requirements:"
for r in sorted(c.get_reqs(req)):
    print '\t', r

print "Distributions:"
for d in c.install_order(req):
    print '\t', filename_dist(d)
