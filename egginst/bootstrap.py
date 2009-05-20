import sys


def main():
    # For now, just use the bootstrap setuptools provides
    from setuptools.command.easy_install import bootstrap
    sys.exit(bootstrap())
