import os
import sys
import re
import getopt
import time
import zipfile
from os.path import basename, dirname, join

from indexed_repo.metadata import (data_from_spec, rawspec_from_dist,
                                   write_index, append_dist)
from indexed_repo import Req



def writestr(z, arcname, data):
    zinfo = zipfile.ZipInfo(filename=arcname,
                            date_time=time.localtime(time.time()))
    # 0x81b6 is what os.stat('file.txt')[0] returns on Linux, where
    # file.txt has mode 0666.
    zinfo.external_attr = 0x81b6 << 16
    z.writestr(zinfo, data)


def zip_repack(zip_src, zip_dst, arc_map={}):
    """
    Repacks a zip-file 'zip_src' to a new zipfile 'zip_dst' with
    updated (or inserted) archives given by 'arc_map'.

    arc_map:
        a dictionary mapping archive names to their content.
        If an archive name maps to None, it is not created in the
        repacked zip-file.
    """
    # zip_src: y   ->   zip_dst: z
    y = zipfile.ZipFile(zip_src)
    z = zipfile.ZipFile(zip_dst, 'w', zipfile.ZIP_DEFLATED)

    # First write all archives from y into z, except the ones which get
    # overwritten (if any).
    for name in y.namelist():
        if name not in arc_map:
            z.writestr(y.getinfo(name), y.read(name))

    # Now, write the new archives.
    for arcname, data in arc_map.iteritems():
        if data is not None:
            writestr(z, arcname, data)

    z.close()
    y.close()


PYC_MAGIC = {
    '\xb3\xf2\r\n': '2.5', # 62131 == ord('\xb3') + ord('\xf2') * 256
    '\xd1\xf2\r\n': '2.6', # 62161 == ord('\xd1') + ord('\xf2') * 256
}
def get_python(z):
    """
    returns the Python version number, if egg contains Python bytecode,
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


REQ_PAT = re.compile(r'''
    (?P<name>[\w\-.]+)               # name
    (\[\w+\])?                       # optional []
    ([\s=<>]*(?P<version>[\w.]+))?   # version
''', re.X)
def convert_requires_txt_line(line):
    """
    parses a single line of the file requires.txt, and returns
    the corresponding spec-style requirement string, or None.
    """
    line = line.strip()
    if not line or line.startswith(('[', '#')):
        return None
    m = REQ_PAT.match(line)
    if m is None:
        print "Warning: requirement %r not recognized" % line
        return None
    if m.group('version'):
        return m.expand(r'\g<name> \g<version>')
    return m.group('name')


def get_requires(z):
    """
    Returns the requirements by reading 'EGG-INFO/requires.txt' as a list
    of spec-style requirement strings.
    """
    arcname = 'EGG-INFO/requires.txt'
    if arcname not in z.namelist():
        return []

    res = []
    names = set()
    for line in z.read(arcname).splitlines():
        req_string = convert_requires_txt_line(line)
        if req_string is None:
            continue
        req = Req(req_string)
        if req.name not in names:
            # only add a new name
            names.add(req.name)
            res.append(req_string)
    return res


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
    spec['packages'] = get_requires(z)
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

# ---------------------------------- CLI ----------------------------------

def try_help(msg):
    print '%s: error: %s, try -h' % (basename(sys.argv[0]), msg)
    sys.exit(1)


def help():
    prog = basename(sys.argv[0])
    print """usage %(prog)s command [options] args

%(prog)s is a tool for creating an indexed repository of eggs which works
with the enpkg command in Enstaller.  All eggs which go into the repository
need to contain additional metadata, which is created by the 'repack' command.
Running the 'index' command will then create the index, such that the
directory (which contains all eggs and the index files) can be servered via
HTTP.

Commands:
=========

index [PATH ...]:
    creates the files index-depend.txt and index-depend.bz2 in the directories
    specified by the arguments (or in the current working directory if no
    argument is given).  All eggs (found in the same directory) with valid
    names are added to the index.

dumpmeta EGG [EGG ...]:
    given indexed eggs, prints their metadata to stdout, i.e. the content of
    the archive 'EGG-INFO/spec/depend'.

repack [-v] EGG [EGG ...]:
    given setuptools egg(s), creates a new egg which contains additional
    metadata, which the other commands use.

update [-v] EGG [EGG ...]:
    updates (or adds) the eggs, given by the arguments, to the index files,
    which must already exist.  Running this command is much faster than
    recreating the entire index, using the 'index' command.
""" % locals()


def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        help()
        return

    if len(sys.argv) < 2:
        try_help("command missing")

    cmd = sys.argv[1]
    try:
        opts, args = getopt.gnu_getopt(sys.argv[2:], 'v', ['verbose'])
    except getopt.GetoptError, err:
        try_help(str(err))

    verbose = False
    for o, a in opts:
        if o in ('-v', '--verbose'):
            verbose = True

    if cmd == 'index':
        for dir_path in args if args else [os.getcwd()]:
            write_index(dir_path, compress=True, verbose=verbose)

    elif cmd == 'dumpmeta':
        for egg_path in args:
            print "==> %s <==" % basename(egg_path)
            print rawspec_from_dist(egg_path)

    elif cmd == 'repack':
        for egg_path in args:
            repack_egg_with_meta(egg_path, verbose)

    elif cmd == 'update':
        for egg_path in args:
            append_dist(egg_path, compress=True, verbose=verbose)

    else:
        try_help("unknown command %r" % cmd)


if __name__ == '__main__':
    main()
