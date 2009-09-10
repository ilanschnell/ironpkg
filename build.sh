#!/bin/bash

EGG=Enstaller-4.0.1-1.egg

rm -rf build dist
python setup.py bdist_egg
cp depend.txt depend
mv dist/Enstaller-*.egg dist/$EGG
egginfo -u spec/depend dist/$EGG
egginfo --sd dist/$EGG
repo-upload --force --no-confirm dist/$EGG
