#!/bin/bash

set -x
set -e


yum -y install gcc glibc glibc-devel libgcc  \
               libxml2-devel libxslt-devel \
               ncurses-libs ncurses-devel \
               readline readline-devel \
               zlib zlib-devel \
               bzip2-libs bzip2-devel \
               gdbm gdbm-devel \
               sqlite sqlite-devel \
               db4 db4-devel \
               openssl openssl-devel \
               libX11 libX11-devel \
               tk tk-devel \
               gcc-c++ \
               gtk2-devel \
               gtk2-engines \
               glib2-devel \
               mesa-libGL mesa-libGL-devel \
               mesa-libGLU mesa-libGLU-devel \
               mesa-libGLw mesa-libGLw-devel \
               gtkglext-libs gtkglext-devel \
               gimp-libs gimp-devel \
               gvfs \
               atk-devel \
               pango-devel \
               cairo-devel \
               freetype-devel \
               fontconfig-devel \
               libcanberra-gtk2 \
               PackageKit-gtk-module \
               make cmake rpm-build

yum -y install git
yum -y wxPython

curl http://python-distribute.org/distribute_setup.py | python
curl https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py | python

pip install ssh
pip install pycrypto
pip install appdirs
pip install requests
pip install pexpect
pip install lxml
pip install psutil

