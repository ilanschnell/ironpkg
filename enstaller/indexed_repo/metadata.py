import os
import sys
import re
import string
import zipfile
from cStringIO import StringIO
from collections import defaultdict
from os.path import basename, isfile, join, getmtime, getsize

from dist_naming import is_valid_eggname
from requirement import Req

from enstaller.utils import md5_file


def parse_index(data):
    """
    Given the data of an index file, such as index-depend.txt, return a
    dictionary mapping the distribution names to the content of the
    corresponding section.
    """
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
    Also this function is a reference for meta-data version 1.1
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
    assert spec['build'] >= 0, spec

    cnames = set()
    for req_string in spec['packages']:
        r = Req(req_string)
        assert r.strictness >= 1
        cnames.add(r.name)
    # make sure no project is listed more than once
    assert len(cnames) == len(spec['packages'])

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


def parse_data(data, index=False):
    """
    Given the content of a dependency spec file, return a dictionary mapping
    the variables to their values.

    If index is True, the MD5, size and mtime are also contained in the
    output dictionary.  It is an error these are missing in the input data.
    """
    spec = {}
    exec data.replace('\r', '') in spec
    assert spec['metadata_version'] >= '1.1', spec

    var_names = [ # these must be present
        'metadata_version', 'name', 'version', 'build',
        'arch', 'platform', 'osdist', 'python', 'packages']
    if index:
        # An index spec also has these
        var_names.extend(['md5', 'size'])
        assert isinstance(spec['md5'], str) and len(spec['md5']) == 32
        assert isinstance(spec['size'], int)
        if 'mtime' in spec:
            var_names.append('mtime')
        if 'commit' in spec:
            var_names.append('commit')

    res = {}
    for name in var_names:
        res[name] = spec[name]
    return res


def parse_depend_index(data):
    """
    Given the data of index-depend.txt, return a dict mapping each distname
    to a dict mapping variable names to their values.
    """
    d = parse_index(data)
    for fn in d.iterkeys():
        # convert the values from a text string (of the spec file) to a dict
        d[fn] = parse_data(d[fn], index=True)
    return d


def rawspec_from_dist(zip_path):
    """
    Returns the raw spec data, i.e. content of spec/depend as a string.
    """
    arcname = 'EGG-INFO/spec/depend'
    z = zipfile.ZipFile(zip_path)
    if arcname not in z.namelist():
        z.close()
        raise KeyError("arcname=%r not in zip-file %s" % (arcname, zip_path))
    data = z.read(arcname)
    z.close()
    return data


def spec_from_dist(zip_path):
    """
    Returns the spec dictionary from a zip-file distribution.
    """
    return parse_data(rawspec_from_dist(zip_path))


def commit_from_dist(zip_path):
    arcname = 'EGG-INFO/spec/__commit__'
    z = zipfile.ZipFile(zip_path)
    if arcname in z.namelist():
        res = 'commit = %r\n' % z.read(arcname).strip()
    else:
        res = ''
    z.close()
    return res


def index_section(zip_path):
    """
    Returns a section corresponding to the zip-file, which can be appended
    to an index.
    """
    return ('==> %s <==\n' % basename(zip_path) +
            'size = %i\n'  % getsize(zip_path) +
            'md5 = %r\n' % md5_file(zip_path) +
            'mtime = %r\n' % getmtime(zip_path) +
            commit_from_dist(zip_path) +
            '\n' +
            rawspec_from_dist(zip_path) + '\n')


def update_index(dir_path, force=False, verbose=False):
    """
    Updates index-depend.txt in the directory specified.
    If index-depend.txt already exists, its content (which contains
    modification time stamps) is used to create the updated file.
    This can be disabled using the force option.
    """
    txt_path = join(dir_path, 'index-depend.txt')
    if verbose:
        print "Updating:", txt_path

    if force or not isfile(txt_path):
        section = {}
    else:
        section = parse_index(open(txt_path).read())

    # since generating the new data may take a while, we first write to memory
    # and then write the file afterwards.
    faux = StringIO()
    for fn in sorted(os.listdir(dir_path), key=string.lower):
        if not fn.endswith('.egg'):
            continue
        if not is_valid_eggname(fn):
            print "WARNING: ignoring invalid egg name:", fn
            continue
        path = join(dir_path, fn)
        if fn in section:
            spec = parse_data(section[fn], index=True)
            if spec.get('mtime') == getmtime(path):
                faux.write('==> %s <==\n' % fn)
                faux.write(section[fn] + '\n')
                continue
        faux.write(index_section(path))
        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()

    if verbose:
        print
    faux.close()
