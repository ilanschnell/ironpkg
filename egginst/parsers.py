import bz2
import re
from collections import defaultdict


def parse_metadata(data, var_names=None):
    """
    Given the content of a dependency file, return a dictionary mapping the
    variables to their values, optionally filtered by var_names.
    """
    d = {}
    exec data in d
    if var_names is None:
        return d

    d2 = {}
    for name in var_names:
        d2[name] = d[name]
    return d2


def parse_index(data):
    """
    Given the bz2 compressed data of an index file, return a dictionary
    mapping the distribution names to the content of the cooresponding
    section.
    """
    data = bz2.decompress(data)

    d = defaultdict(list)
    sep_pat = re.compile(r'==>\s+(\S+)\s+<==')
    for line in data.splitlines():
        m = sep_pat.match(line)
        if m:
            fn = m.group(1)
            continue
        d[fn].append(line.rstrip())

    d2 = {}
    for k in d.iterkeys():
        d2[k] = '\n'.join(d[k])

    return d2


_DEPEND_VARS = [
    'metadata_version', 'md5', 'name', 'version', 'disttype',
    'arch', 'platform', 'osdist', 'python', 'packages',
]
def parse_depend_index(data):
    """
    Given the data of index-depend.bz2, return a dict mapping each eggname
    to a dict mapping variable names to their values.
    """
    d = parse_index(data)
    for k in d.iterkeys():
        d[k] = parse_metadata(d[k], _DEPEND_VARS)
    return d
