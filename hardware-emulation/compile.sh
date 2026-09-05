#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

nvcc "$SCRIPT_DIR/static_emu_new.cu" \
  -o "$SCRIPT_DIR/static_emu_new" \
  -ccbin mpicxx \
  -O3 \
  -I"${NCCL_HOME}/include" \
  -L"${NCCL_HOME}/lib" \
  -lnccl \
  -lcudart
