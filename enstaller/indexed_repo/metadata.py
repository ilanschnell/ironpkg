import bz2
import re
import string
from collections import defaultdict

from utils import canonical



def parse_index(data):
    """
    Given the bz2 compressed data of an index file, return a dictionary
    mapping the distribution names to the content of the cooresponding
    section.
    """
    data = bz2.decompress(data)

    d = defaultdict(list)
    sep_pat = re.compile(r'==>\s*(\S+)\s*<==')
    for line in data.splitlines():
        m = sep_pat.match(line)
        if m:
            fn = m.group(1)
            continue
        d[fn].append(line.rstrip())

    res = {}
    for fn in d.iterkeys():
        res[fn] = '\n'.join(d[fn])
    return res


def data_from_spec(spec):
    """
    Given a spec dictionary, returns a the spec file as a well formed string.
    Also this function is a reference for metadata version 1.1
    """
    str_None = str, type(None)
    for var, typ in [
        ('name', str), ('version', str), ('build', int),
        ('arch', str_None), ('platform', str_None), ('osdist', str_None),
        ('python', str_None), ('packages', list)]:
        assert isinstance(spec[var], typ), spec
        if isinstance(spec[var], str):
            s = spec[var]
            assert s == s.strip(), spec
            assert s != '', spec
    assert spec['build'] > 0

    canon_names = set()
    for req_string in spec['packages']:
        assert isinstance(req_string, str), req_string
        canon_names.add(canonical(req_string.split()[0]))
    # make sure no project is listed more than once
    assert len(canon_names) == len(spec['packages'])

    lst = ["""\
metadata_version = '1.1'
name = %(name)r
version = %(version)r
build = %(build)i

arch = %(arch)r
platform = %(platform)r
osdist = %(osdist)r
python = %(python)r""" % spec]

    if spec['packages']:
        lst.append('packages = [')
        deps = spec['packages']
        for req in sorted(deps, key=string.lower):
            lst.append("  %r," % req)
        lst.append(']')
    else:
        lst.append('packages = []')

    lst.append('')
    return '\n'.join(lst)


def parse_data(data, index):
    """
    Given the content of a dependency spec file, return a dictionary mapping
    the variables to their values.
    """
    spec = {}
    exec data in spec
    assert spec['metadata_version'] in ('1.0', '1.1'), spec

    var_names = [ # these must be present
        'metadata_version', 'name', 'version', 'build',
        'arch', 'platform', 'osdist', 'python', 'packages']
    if index:
        # An index spec also has these
        var_names.extend(['md5', 'size'])
        assert isinstance(spec['md5'], str) and len(spec['md5']) == 32
        assert isinstance(spec['size'], int)

    if spec['metadata_version'] == '1.0':
        # convert 1.0 -> 1.1
        spec['metadata_version'] = '1.1'

        assert spec['filename'].endswith('.egg')
        n, v, b = spec['filename'][:-4].split('-')
        assert canonical(n) == canonical(spec['name'])
        assert v == spec['version']
        assert b >= 1
        spec['build'] = int(b)
        pkgs = spec['packages']
        spec['packages'] = [name + " " + pkgs[name]
                            for name in sorted(pkgs, key=string.lower)]
    res = {}
    for name in var_names:
        res[name] = spec[name]
    return res


def parse_depend_index(data):
    """
    Given the data of index-depend.bz2, return a dict mapping each distname
    to a dict mapping variable names to their values.
    """
    d = parse_index(data)
    for fn in d.iterkeys():
        # convert the values from a text string (of the spec file) to a dict
        d[fn] = parse_data(d[fn], index=True)
    return d
