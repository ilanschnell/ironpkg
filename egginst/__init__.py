"""
"""

from egginst import EggInst


# API:
def egginst(path, remove=False, verbose=False):
    """
    """
    ei = EggInst(path, verbose)
    if remove:
        ei.remove()
    else:
        ei.install()
