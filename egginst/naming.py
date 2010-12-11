def canonical(s):
    """
    Return the canonical representations of a project name.
    """
    return s.lower().replace('-', '_')


def name_version_fn(fn):
    """
    Given the filename of a package, returns a tuple(name, version).
    """
    if fn.endswith('.egg'):
        fn = fn[:-4]
    if '-' in fn:
        return tuple(fn.split('-', 1))
    else:
        return fn, ''


def cname_fn(fn):
    """
    Return the canonical project name, given the filename.
    """
    return canonical(name_version_fn(fn)[0])
