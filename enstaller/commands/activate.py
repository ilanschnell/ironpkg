from distutils import log

from enstaller.command.enstaller import enstaller

class activate(enstaller):
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.initialize()

    def activate(self, package_objs):
        if not isinstance(package_objs, list):
            package_objs = [package_objs]
        for pkg in package_objs:
            pkg.activate()
