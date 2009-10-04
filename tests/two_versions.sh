#!/bin/bash

# Example to illustrate how to use two versions of the same package
# in a single Python process.

A=$HOME/fooA
B=$HOME/fooB

PKG=argparse

rm -rf $A $B
enpkg --prefix $A -f $PKG 0.8.0
enpkg --prefix $B -f $PKG 1.0

SITE=lib/python2.5/site-packages

sed -e "s:_A_:$A/$SITE:" -e "s:_B_:$B/$SITE:" -e "s:PKG:$PKG:"  <<EOF >t.py
import sys

sys.path.insert(0, '_A_')
import PKG
print "A:", PKG.__version__

sys.path.insert(0, '_B_')
reload(PKG)
print "B:", PKG.__version__

EOF

python t.py
