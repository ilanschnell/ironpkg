#!/bin/bash

VER=4.1.0


SPEC=Enstaller.egg-info/spec
mkdir -p $SPEC
sed -e "s/XXX/$VER/" <<EOF >$SPEC/depend
metadata_version = '1.1'
name = 'Enstaller'
version = 'XXX'
build = 1

arch = None
platform = None
osdist = None
python = '2.5'
packages = []
EOF


EGG=dist/Enstaller-$VER-1.egg
rm -rf build dist
python setup.py bdist_egg
mv dist/Enstaller-*.egg $EGG

# egginfo --sd $EGG
# repo-upload --force --no-confirm $EGG
