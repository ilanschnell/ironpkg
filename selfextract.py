"""\
Self installs IronPkg into the current IronPython environment.
egg: EGGNAME
md5: EGGMD5

Options:
  -h, --help     show this help message and exit
  --install      self install
"""
import os
import sys
import base64
import hashlib
import tempfile
import zipfile
from os.path import dirname, isdir, join


b64eggdata = 'EGGDATA'


def unzip(zip_file, dir_path):
    """Unzip the zip_file into the directory dir_path."""
    z = zipfile.ZipFile(zip_file)
    for name in z.namelist():
        if name.endswith('/'):
            continue
        path = join(dir_path, *name.split('/'))
        if not isdir(dirname(path)):
            os.makedirs(dirname(path))
        fo = open(path, 'wb')
        fo.write(z.read(name))
        fo.close()
    z.close()


def self_install():
    tmp_dir = tempfile.mkdtemp()
    egg_path = join(tmp_dir, 'EGGNAME')
    data = base64.b64decode(b64eggdata)
    assert hashlib.md5(data).hexdigest() == 'EGGMD5'
    fo = open(egg_path, 'wb')
    fo.write(data)
    fo.close()
    unzip(egg_path, tmp_dir)
    sys.path.insert(0, tmp_dir)
    import egginst
    print "Bootstrapping:", egg_path
    ei = egginst.EggInst(egg_path)
    ei.install()


if __name__ == '__main__':
    if '--install' in sys.argv:
        self_install()
    else:
        print __doc__
