rm -rf dist build notest.egg-info
python setup.py sdist bdist
rm dist/*.zip
twine upload dist/*
