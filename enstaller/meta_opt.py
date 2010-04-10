import bz2
from cStringIO import StringIO

from utils import canonical, write_data_from_url
from indexed_repo.metadata import parse_index


URL = 'http://www.enthought.com/epd/index-meta.bz2'


def get_meta(url):
    faux = StringIO()
    write_data_from_url(faux, url)
    index_data = faux.getvalue()
    faux.close()

    if url.endswith('.bz2'):
        index_data = bz2.decompress(index_data)

    res = {}
    for name, data in parse_index(index_data).iteritems():
        d = {}
        exec data.replace('\r', '') in d
        cname = canonical(name)
        res[cname] = {}
        for var_name in ['name', 'homepage', 'doclink', 'license',
                         'summary', 'description']:
            res[cname][var_name] = d[var_name]
    return res


t = get_meta(URL)
print t['bitarray']['description']
