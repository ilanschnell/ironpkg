import os
import sys

from enstaller.indexed_repo import Chain, Req, filename_dist


cwd = os.getcwd()

c = Chain(verbose=0)
c.add_repo('file://%s/' % cwd, 'repo1.txt')
c.add_repo('file://%s/' % cwd, 'repo_pub.txt')
c.test()

#req = Req(' '.join(sys.argv[1:]))
req = Req('foo')#, '2.6')
print repr(req)

if 0:
    print "Requirements:"
    for r in sorted(rs):
        print '\t%-40r %s' % (r, filename_dist(rs[r]))

if 1:
    print "Distributions:"
    for d in c.install_order(req, 1):
        print '\t', filename_dist(d)

Req(' ')
