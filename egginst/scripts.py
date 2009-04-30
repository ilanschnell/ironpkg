import os
import sys
from os.path import basename


def create(path, entry_pt, egg=None):
    print 'Creating script', path

    assert entry_pt.count(':') == 1
    module, func = entry_pt.strip().split(':')

    fo = open(path, 'w')
    fo.write('''\
#!%(python)s
#
#     %(egg_name)s
#
from %(module)s import %(func)s

%(func)s()
''' % dict(module=module, func=func, python=sys.executable,
           egg_name=(basename(egg.fpath) if egg is not None else egg)))
    fo.close()
    os.chmod(path, 0755)
