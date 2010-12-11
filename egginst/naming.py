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


if __name__ == '__main__':
    for fn, name, ver, cname in [
        ('NumPy-1.5-py2.6-win32.egg', 'NumPy', '1.5-py2.6-win32', 'numpy'),
        ('NumPy-1.5-2.egg', 'NumPy', '1.5-2', 'numpy'),
        ('NumPy-1.5.egg', 'NumPy', '1.5', 'numpy'),
        ('Cython.egg', 'Cython', '', 'cython'),
        ('Foo.zip', 'Foo.zip', '', 'foo.zip'),
        ]:
        assert name_version_fn(fn) == (name, ver)
        assert cname_fn(fn) == canonical(name) == cname
    assert canonical('MySQL-Python') == 'mysql_python'
