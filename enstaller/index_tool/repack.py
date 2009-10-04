import os
import re
import time
import zipfile
from os.path import basename, dirname, join

from ziputils import zip_repack

from enstaller.indexed_repo.metadata import data_from_spec


PYC_MAGIC = {
    '\xb3\xf2\r\n': '2.5', # 62131 == ord('\xb3') + ord('\xf2') * 256
    '\xd1\xf2\r\n': '2.6', # 62161 == ord('\xd1') + ord('\xf2') * 256
}
def get_python(z):
    """
    returns the Python version number, if egg contains Python code,
    and None otherwise.
    """
    heads = [z.read(name)[:4]
             for name in z.namelist()
             if (name.endswith(('.pyc', '.pyo')) and
                 not name.startswith('EGG-INFO/'))]
    if heads == []:
        return None
    h0 = heads[0]
    # Make sure all .pyc heads are the same
    assert all(h == h0 for h in heads)
    return PYC_MAGIC[h0]


def spec_from_egg(egg_path):
    """
    Given the path to an egg, do whatever necessary to return spec dictionary.
    """
    egg_name = basename(egg_path)
    assert egg_name.endswith('.egg') and egg_name.count('-') >= 2
    spec = dict(build=1, arch=None, platform=None, osdist=None)
    spec['name'], spec['version'] = egg_name.split('-')[:2]

    z = zipfile.ZipFile(egg_path)
    spec['python'] = get_python(z)
    spec['packages'] = [] # TODO
    z.close()
    return spec


def repack_egg_with_meta(src_path, verbose=False):
    """
    Updates an egg with spec data
    """
    spec = spec_from_egg(src_path)

    dst_name = '%(name)s-%(version)s-%(build)i.egg' % spec
    dst_path = join(dirname(src_path), dst_name)
    if verbose:
        print "New egg path:", dst_path

    spec_depend = data_from_spec(spec)
    if verbose:
        print 20*'-' + '\n' + spec_depend + 20*'-'

    # maps arcnames to their content
    arcmap = {'EGG-INFO/spec/depend': spec_depend}

    if src_path == dst_path:
        tmp_path = src_path + '-tmp'
        zip_repack(src_path, tmp_path, arcmap)
        os.unlink(src_path)
        os.rename(tmp_path, dst_path)
    else:
        zip_repack(src_path, dst_path, arcmap)
