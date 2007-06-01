This is a python module which exposes the api used in python's bdist_wininst
built executables. When a python package is packaged into an installable
executable, a custom python interpreter is used which has several methods
accessed during post-install for things like creating shortcuts.

The majority of the code is from Python's source, just exposed as a python
extension so it can be used for post-install steps by the enstaller app.

This extension probably needs to be built with a microsoft compiler.