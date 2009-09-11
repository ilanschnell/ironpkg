# this test code is not imported anywhere

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
