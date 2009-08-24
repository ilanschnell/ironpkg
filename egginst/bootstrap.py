

def main():
    """
    To bootstrap Enstaller into a Python environment, used the following
    code:

    sys.path.insert(0, '/path/to/Enstaller.egg')
    from egginst.bootstrap import main
    exitcode = main()
    """
    # For now, just use the bootstrap setuptools provides
    from setuptools.command.easy_install import bootstrap

    return bootstrap()
