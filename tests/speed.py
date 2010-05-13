import os
import hashlib

from enstaller.indexed_repo import Chain, Req, filename_dist, dist_as_req
import enstaller.indexed_repo.requirement as requirement


c = Chain(verbose=0)
for fn in ['index-5.1.txt', 'index-5.0.txt']:
    c.add_repo('file://%s/' % os.getcwd(), fn)


requirement.PY_VER = '2.5'
h = hashlib.new('md5')
# This is quite expensive and takes about 2.3 seconds on my 2GHz MacBock
for dist in c.install_order(Req('epd 5.1.0'), True):
    for d in c.install_order(dist_as_req(dist)):
        h.update(d)
assert h.hexdigest() == '6c4c583bdb87634729c55bf23140f36d'
