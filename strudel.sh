#!/bin/bash

STRUDEL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LD_LIBRARY_PATH="${STRUDEL_DIR}":$LD_LIBRARY_PATH
"${STRUDEL_DIR}"/launcher
