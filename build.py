import os
import base64
import hashlib
import zipfile
from os.path import join

from enstaller import __version__
from enstaller.indexed_repo.metadata import data_from_spec


SPEC = dict(
    name="ironpkg",
    version=__version__,
    build=1,
    arch=None,
    platform='cli',
    osdist=None,
    python=None,
    packages=[],
)


def build_egg(spec):
    fn = '%(name)s-%(version)s-%(build)s.egg' % spec
    z = zipfile.ZipFile(fn, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk('.'):
        if not root[2:].startswith(('egginst', 'enstaller')):
            continue
        for fn in files:
            if not fn.endswith('.py'):
                continue
            path = join(root, fn)
            z.write(path, path[2:].replace('\\', '/'))
    z.writestr('EGG-INFO/spec/depend', data_from_spec(spec))
    z.writestr('EGG-INFO/entry_points.txt', """[console_scripts]
ironegg = egginst.main:main
ironpkg = enstaller.main:main
""")
    z.close()


def build_py(spec):
    eggname = '%(name)s-%(version)s-%(build)s.egg' % spec
    eggdata = open(eggname, 'rb').read()
    eggmd5 = hashlib.md5(eggdata).hexdigest()
    code = open('selfextract.py', 'r').read()
    code = code.replace('EGGNAME', eggname)
    code = code.replace('EGGDATA', base64.b64encode(eggdata))
    code = code.replace('EGGMD5', eggmd5)
    fo = open('%(name)s-%(version)s.py' % spec, 'w')
    fo.write(code)
    fo.close()


if __name__ == '__main__':
    build_egg(SPEC)
    build_py(SPEC)
