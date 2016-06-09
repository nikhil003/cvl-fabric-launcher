#!/bin/bash

STRUDEL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

## --- This can be a fix for systems, where libgio-2.0 is different to the build environment ---
## add included libgio if not avail on system - use system if avail
#LIBGIO_PATH=$(/sbin/ldconfig -p | grep  libgio-2.0.so.0)
#if [ -z "$LIBGIO_PATH" ]; then
#  echo "WARNING: libgio-2.0.so.0 not found on system - using build in version"
#  LD_LIBRARY_PATH="${STRUDEL_DIR}"/bin/libgio:$LD_LIBRARY_PATH
#fi

if [ -f "${STRUDEL_DIR}"/launcher ]; then
  LD_LIBRARY_PATH="${STRUDEL_DIR}":$LD_LIBRARY_PATH
  "${STRUDEL_DIR}"/launcher
elif [ -f "${STRUDEL_DIR}"/bin/launcher ]; then
  LD_LIBRARY_PATH="${STRUDEL_DIR}/bin":$LD_LIBRARY_PATH
  "${STRUDEL_DIR}"/bin/launcher
else
  echo "ERROR: Cannot find launcher."
fi

