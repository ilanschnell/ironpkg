import sys

try:
    import setuptools
except:
    pass
    
def configuration(parent_package='enstaller',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('wininst',parent_package,top_path)
    config.set_options(ignore_setup_xxx_py=True,
                       assume_default_configuration=True,
                       delegate_options_to_subpackages=True,
                       quiet=True)

    win_libs = ["comctl32",  "kernel32", "user32", "gdi32", "winspool", "comdlg32", "advapi32", "shell32", "ole32", "oleaut32", "uuid", "odbc32", "odbccp32"]
    config.add_extension("wininst",["wininst.c"], libraries=win_libs)
    config.add_data_files('*.txt')
    
    return config
    
if __name__ == "__main__":
    if sys.platform == 'win32':
        from numpy.distutils.core import setup
        setup(version='1.0.0',
              description  = 'Python API used during windows installers',
              author       = 'Enthought, Inc',
              author_email = 'info@enthought.com',
              url          = 'http://code.enthought.com',
              license      = 'BSD',
              configuration=configuration)
