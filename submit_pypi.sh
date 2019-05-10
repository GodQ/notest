#!/usr/bin/env bash
rm -rf dist build notest.egg-info
python setup.py sdist bdist
twine upload dist/*