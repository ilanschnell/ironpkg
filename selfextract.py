import sys
import zipfile
from os.path import join
from optparse import OptionParser


eggdata = "EGGDATA"

def cli():
    egg_path = join("EGGNAME")
    fo = open(egg_path, 'wb')
    fo.write(eggdata)
    fo.close()
    sys.path.insert(0, egg_path)
    from egginst.bootstrap import main
    main()


if __name__ == '__main__':
    cli()
