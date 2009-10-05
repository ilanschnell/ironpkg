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

def parse_requires(txt):
    result = []
    for line in txt.splitlines():
        req_string = convert_requires_txt_line(line)
        if req_string is None:
            continue
        req = Req(req_string)
        if req.name not in set(Req(r).name for r in result):
            result.append(req_string)
    return result

def get_requires(z):
    """
    Returns the requirements by reading 'EGG-INFO/requires.txt' as a list
    of spec/depend-style requirement strings.
    """
    arcname = 'EGG-INFO/requires.txt'
    if arcname in z.namelist():
        return parse_requires(z.read(arcname))
    return []


def spec_from_egg(egg_path):
    """
    Given the path to an egg, do whatever necessary to return spec dictionary.
    """
    egg_name = basename(egg_path)
    assert egg_name.endswith('.egg') and egg_name.count('-') >= 2
    z = zipfile.ZipFile(egg_path)
    spec = dict(
        build = 1,
        arch = None,
        platform = 'win32' if '-win32' in egg_name else None,
        osdist = None,
        python = get_python(z),
        packages = get_requires(z),
    )
    z.close()
    spec['name'], spec['version'] = egg_name.split('-')[:2]
    return spec


def repack_egg(src_path, overwrite=None, verbose=False):
    """
    Updates an egg with spec data
    """
    spec = spec_from_egg(src_path)

    if overwrite:
        d = {}
        execfile(overwrite, d)
        spec.update(d)

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
need to contain additional metadata.  These new eggs are created from
ordinary setuptools eggs using the 'repack' command.
Running the 'index' command will then create the index, such that the
directory (which contains all eggs and the index files) can be served to
enpkg over HTTP.

Commands:
=========

index [-v] [PATH ...]:
    creates the files index-depend.txt and index-depend.bz2 in the directories
    specified by the arguments (or in the current working directory if no
    argument is given).  All eggs (found in the same directory) with valid
    names are added to the index.

dumpmeta EGG [EGG ...]:
    given indexed eggs, prints their metadata to stdout, i.e. the content of
    the archive 'EGG-INFO/spec/depend'.

repack [-o PATH] [-v] EGG [EGG ...]:
    given setuptools egg(s), creates a new egg which contains additional
    metadata, which the other commands use.  The -o, --overwrite option takes
    a Python file (which defines metadata variables).  Variable(s) defined in
    this file overwrite the default setting the repack command determines by
    analyzing the content of the setuptools egg.

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
        opts, args = getopt.gnu_getopt(sys.argv[2:],
                                       'vo:', ['verbose', 'overwrite='])
    except getopt.GetoptError, err:
        try_help(str(err))

    verbose = False
    overwrite = None
    for o, a in opts:
        if o in ('-v', '--verbose'):
            verbose = True
        elif o in ('-o', '--overwrite'):
            overwrite = a

    if cmd == 'index':
        for dir_path in args if args else [os.getcwd()]:
            write_index(dir_path, compress=True, verbose=verbose)

    elif cmd == 'dumpmeta':
        for egg_path in args:
            print "==> %s <==" % basename(egg_path)
            print rawspec_from_dist(egg_path)

    elif cmd == 'repack':
        for egg_path in args:
            repack_egg(egg_path, overwrite, verbose)

    elif cmd == 'update':
        for egg_path in args:
            append_dist(egg_path, compress=True, verbose=verbose)

    else:
        try_help("unknown command %r" % cmd)


if __name__ == '__main__':
    main()
