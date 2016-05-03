#!/bin/bash

STRUDEL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f launcher ]; then
  LD_LIBRARY_PATH="${STRUDEL_DIR}":$LD_LIBRARY_PATH
  "${STRUDEL_DIR}"/launcher
elif [ -f bin/launcher ]; then
  LD_LIBRARY_PATH="${STRUDEL_DIR}/bin":$LD_LIBRARY_PATH
  "${STRUDEL_DIR}"/bin/launcher
else
  echo "ERROR: Cannot find launcher."
fi  

