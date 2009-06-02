"""
"""

from egginst import EggInst


# API:
def egginst(path, remove=False):
    """
    """
    ei = EggInst(path)
    if remove:
        ei.remove()
    else:
        ei.install()
