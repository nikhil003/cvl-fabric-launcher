#!/bin/bash

set -x
set -e

curl http://python-distribute.org/distribute_setup.py | python
curl https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | python

pip install --upgrade ssh
pip install --upgrade pycrypto
pip install --upgrade appdirs
pip install --upgrade requests
