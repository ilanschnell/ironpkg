from distutils import log

from enstaller import enstaller

class list_packages(enstaller):
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.initialize()
        self.list_packages(self.args)

    def list_packages(self, package_specs):
        for pkg in self.get_installed_packages(package_specs):
            print pkg.name, pkg.version, pkg.active, pkg.location

    def get_installed_packages(self, package_specs=[]):
        """
        Returns a list of packages in self.pythonpath which match package_specs.
        Returns all packages if no package_specs given.
        """
        pkg_list = []
        for repo in self.pythonpath:
            pkg_list += repo.find_packages(package_specs)
        return pkg_list

