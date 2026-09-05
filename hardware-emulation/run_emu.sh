#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXE="$SCRIPT_DIR/static_emu_new"
HOSTFILE="${HOSTFILE:-$SCRIPT_DIR/hostfile}"
NP="${NP:-8}"
OUTPUT="$SCRIPT_DIR/static_results.csv"

PERMS=(
  "1 2 3 4 5 6 7 0"   # distance 1
  "2 3 4 5 6 7 0 1"   # distance 2
  "4 5 6 7 0 1 2 3"   # distance 4
)

MSG_SIZES=(
  1 2 4 8 16 32 64 128 256 512
  1024 2048 4096 8192 16384
  24576 32768 49152 65536
  98304 131072 196608 262144
  393216 524288 786432
  1048576 1572864 2097152
  3145728 4194304
  6291456 8388608
  12582912 16777216
  25165824 33554432
  50331648 67108864
  100663296 134217728
  201326592 268435456
  402653184 536870912
  805306368 1073741824
  2147483648 4294967295
)

MSG_SIZE_ORDER=(
  "1B" "2B" "4B" "8B" "16B" "32B" "64B" "128B" "256B" "512B"
  "1KB" "2KB" "4KB" "8KB" "16KB"

  "24KB" "32KB" "48KB" "64KB"
  "96KB" "128KB" "192KB" "256KB"
  "384KB" "512KB" "768KB"

  "1MB" "1.5MB" "2MB"
  "3MB" "4MB"
  "6MB" "8MB"
  "12MB" "16MB"

  "24MB" "32MB"
  "48MB" "64MB"
  "96MB" "128MB"
  "192MB" "256MB"
  "384MB" "512MB"
  "768MB" "1GB"
  "2GB" "4GB"
)

echo "Size,FullTime,EnqueueTime,WaitTime,BaseSize,PermIndex,Shift" > "$OUTPUT"

echo "Starting benchmarks..."

for base_size in "${MSG_SIZES[@]}"; do

  for i in "${!PERMS[@]}"; do
    perm="${PERMS[$i]}"

    # Define shift ranges per permutation
    if [[ "$i" -eq 0 ]]; then
      shifts=(1 2 3)
    elif [[ "$i" -eq 1 ]]; then
      shifts=(2 3)
    else
      shifts=(3)
    fi

    for shift in "${shifts[@]}"; do

      adj_size=$(( base_size >> shift ))

      if [[ "$adj_size" -le 0 ]]; then
        continue
      fi

      echo "Running base=$base_size adjusted=$adj_size perm=$i shift=$shift"
      #result=$(mpirun -x NCCL_DEBUG_SUBSYS=INIT,NET --hostfile $HOSTFILE -x NCCL_DEBUG=DEBUG nswrap $EXE $perm $adj_size)
      result=$(mpirun -np $NP --mca orte_base_help_aggregate 0 -x NCCL_DEBUG_SUBSYS=INIT,NET --tag-output  --hostfile $HOSTFILE -x NCCL_DEBUG=DEBUG nswrap $EXE $perm $adj_size)

      echo "$result,$base_size,$((i+1)),$shift" >> "$OUTPUT"
      echo "$result,$base_size,$((i+1)),$shift"

      sleep 1
    done
  done

done

echo "Done! Results saved to $OUTPUT"
