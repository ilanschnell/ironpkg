import os
import zipfile
from os.path import join

from enstaller import __version__
from enstaller.indexed_repo.metadata import data_from_spec


spec = dict(
    name="ironpkg",
    version=__version__,
    build=1,
    arch='x86',
    platform='cli',
    osdist=None,
    python=None,
    packages=[],
)


def build_egg(path):
    z = zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED)
    for root, dirs, files in os.walk('.'):
        if not root[2:].startswith(('egginst', 'enstaller')):
            continue
        for fn in files:
            if not fn.endswith('.py'):
                continue
            path = join(root, fn)
            z.write(path, path[2:].replace('\\', '/'))
    z.writestr('EGG-INFO/spec/depend', data_from_spec(spec))
    z.close()


if __name__ == '__main__':
    build_egg('%(name)s-%(version)s-%(build)s.egg' % spec)
