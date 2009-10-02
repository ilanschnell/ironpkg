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
cat <<EOF >header.sh
#!/bin/sh
exec python -c "import sys, os; sys.path.insert(0, os.path.abspath('\$0')); from egginst.bootstrap import cli; cli()" "\$@"
EOF
cat header.sh dist/Enstaller-*-py*.egg >$EGG
rm -f dist/Enstaller-*-py*.egg
chmod +x $EGG

# egginfo --sd $EGG
# repo-upload --force --no-confirm $EGG
