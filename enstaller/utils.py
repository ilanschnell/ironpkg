import bz2
import sys
import hashlib
import urlparse
import urllib2
from cStringIO import StringIO
from os.path import abspath, expanduser

from egginst.utils import human_bytes, rm_rf
from egginst.naming import canonical
from enstaller import __version__
from enstaller.verlib import NormalizedVersion, IrrationalVersionError


PY_VER = '%i.%i' % sys.version_info[:2]


def abs_expanduser(path):
    return abspath(expanduser(path))


def comparable_version(version):
    """
    Given a version string (e.g. '1.3.0.dev234'), return an object which
    allows correct comparison. For example:
        comparable_version('1.3.10') > comparable_version('1.3.8')  # True
    whereas:
        '1.3.10' > '1.3.8'  # False
    """
    try:
        # This hack makes it possible to use 'rc' in the version, where
        # 'rc' must be followed by a single digit.
        ver = version.replace('rc', '.dev99999')
        return NormalizedVersion(ver)
    except IrrationalVersionError:
        # If obtaining the RationalVersion object fails (for example for
        # the version '2009j'), simply return the string, such that
        # a string comparison can be made.
        return version


def md5_file(path):
    """
    Returns the md5sum of the file (located at `path`) as a hexadecimal
    string of length 32.
    """
    fi = open(path, 'rb')
    h = hashlib.new('md5')
    while True:
        chunk = fi.read(65536)
        if not chunk:
            break
        h.update(chunk)
    fi.close()
    return h.hexdigest()


def open_with_auth(url):
    """
    Open a urllib2 request, handling HTTP authentication
    """
    import enstaller.config as config
    try:
        import custom_tools
    except ImportError:
        custom_tools = None

    scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
    assert not query
    auth, host = urllib2.splituser(netloc)
    if (auth is None and custom_tools and
                hasattr(custom_tools, 'epd_baseurl') and
                url.startswith(custom_tools.epd_baseurl)):
        conf = config.read()
        if conf is None:
            raise Exception("Could not locate Enstaller configuration file")
        userpass = conf.get('EPD_userpass')
        if userpass:
            auth = userpass
        else:
            print "WARNING: EPD_userpass missing in: %s" % config.get_path()
    if auth:
        coded_auth = "Basic " + urllib2.unquote(auth).encode('base64').strip()
        new_url = urlparse.urlunparse((scheme, host, path,
                                       params, query, frag))
        request = urllib2.Request(new_url)
        request.add_header("Authorization", coded_auth)
    else:
        request = urllib2.Request(url)
    request.add_header('User-Agent', 'Enstaller/%s' % __version__)
    return urllib2.urlopen(request)


def write_data_from_url(fo, url, md5=None, size=None):
    """
    Read data from the url and write to the file handle fo, which must be
    open for writing.  Optionally check the MD5.  When the size in bytes
    is provided, a progress bar is displayed using the download/copy.
    """
    if size:
        sys.stdout.write('%9s [' % human_bytes(size))
        sys.stdout.flush()
        n = cur = 0

    if url.startswith('file://'):
        path = url[7:]
        fi = open(path, 'rb')
    elif url.startswith('http://'):
        try:
            fi = open_with_auth(url)
        except urllib2.URLError, e:
            raise urllib2.URLError("\n%s\nCannot open URL:\n    %s" % (e, url))
    else:
        raise Exception("Invalid url: %r" % url)

    h = hashlib.new('md5')

    if size and size < 16384:
        buffsize = 1
    else:
        buffsize = 256

    while True:
        chunk = fi.read(buffsize)
        if not chunk:
            break
        fo.write(chunk)
        if md5:
            h.update(chunk)
        if not size:
            continue
        n += len(chunk)
        if float(n) / size * 64 >= cur:
            sys.stdout.write('.')
            sys.stdout.flush()
            cur += 1

    if size:
        sys.stdout.write(']\n')
        sys.stdout.flush()

    fi.close()

    if md5 and h.hexdigest() != md5:
        sys.stderr.write("FATAL ERROR: Data received from\n\n"
                         "    %s\n\n"
                         "is corrupted.  MD5 sums mismatch.\n" % url)
        fo.close()
        sys.exit(1)


def get_info(url):
    """
    Returns a dict mapping canonical project names to spec structures
    containing additional meta-data of the project which is not contained
    in the index-depend data.
    """
    from indexed_repo.metadata import parse_index

    faux = StringIO()
    write_data_from_url(faux, url)
    index_data = faux.getvalue()
    faux.close()

    if url.endswith('.bz2'):
        index_data = bz2.decompress(index_data)

    res = {}
    for name, data in parse_index(index_data).iteritems():
        d = {}
        exec data.replace('\r', '') in d
        cname = canonical(name)
        res[cname] = {}
        for var_name in ['name', 'homepage', 'doclink', 'license',
                         'summary', 'description']:
            res[cname][var_name] = d[var_name]
    return res
