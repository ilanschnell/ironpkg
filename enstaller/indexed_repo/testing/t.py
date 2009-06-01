import sys
import os
from os.path import basename

from enstaller.indexed_repo.repo import IndexedRepo, Req
from enstaller.indexed_repo.utils import filename_dist


ir = IndexedRepo(verbose=False)

ir.add_repo('file://%s/' % os.getcwd(), 'repo1.txt')

req = Req(sys.argv[1])
print '===========', req
print '-----------', filename_dist(ir.get_dist(req))

#for r in sorted(ir.get_reqs(req)):
#    print '\t', r

for d in ir.install_order(req):
    print '\t', basename(d)
