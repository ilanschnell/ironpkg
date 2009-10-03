# this test code is not imported anywhere
import xmlrpclib
import sys

pypi = xmlrpclib.ServerProxy('http://python.org/pypi')
for hit in pypi.search(dict(name=sys.argv[1])):
    print '''\
NAME: %(name)s %(version)s
SUMM: %(summary)s''' % hit
    urls = pypi.package_urls(hit['name'], hit['version'])
    if urls:
        for url in urls:
            #print repr(url)
            print '''\
%(url)s
\t filename: %(filename)s (%(size)i bytes)
\t pkgtype : %(packagetype)s
\t py-vers : %(python_version)s''' % url

    print



sys.exit()

import re
import StringIO

import enstaller.utils as utils



URL = 'http://pypi.python.org/simple/'

if 0:
    faux = StringIO.StringIO()
    utils.write_data_from_url(faux, URL)
    data = faux.getvalue()

data = open('simple.txt').read()

pat = re.compile(r'<a href=.+?>(.+?)<')

for line in data.splitlines():
    m = pat.match(line)
    if m:
        print m.group(1)
