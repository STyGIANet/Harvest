#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXE="$SCRIPT_DIR/static_emu_new"
HOSTFILE="${HOSTFILE:-$SCRIPT_DIR/hostfile}"
NP="${NP:-8}"
OUTPUT="$SCRIPT_DIR/alpha-beta.csv"

# PERMS=(
#   "1 2 3 4 5 6 7 0"
#   "2 3 4 5 6 7 0 1"
#   "3 4 5 6 7 0 1 2"
#   "4 5 6 7 0 1 2 3"
#   "5 6 7 0 1 2 3 4"
#   "6 7 0 1 2 3 4 5"
#   "7 0 1 2 3 4 5 6"
# )

PERMS=(
  "1 2 3 4 5 6 7 0" # distance 1
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
)

# Updated Header
echo "Size,FullTime,EnqueueTime,WaitTime,MsgName,distance" > "$OUTPUT"

echo "Starting benchmarks..."
for i in "${!PERMS[@]}"; do
  perm="${PERMS[$i]}"

  # Use !MSG_SIZES to get the indices 0 through 8
  for j in "${!MSG_SIZES[@]}"; do
    size=${MSG_SIZES[$j]}
    name=${MSG_SIZE_ORDER[$j]} # Get the human-readable name
    
    # Run mpirun and append the name to the end of the output line
    # We use 'tr -d \n' or similar if mpirun output doesn't handle the trailing comma well
    adj_size=$(( size ))
    echo "Running step_id=$i perm=[$perm], size=$adj_size ($name)"
    echo "$perm"
    result=$(mpirun -np $NP --hostfile $HOSTFILE nswrap $EXE $perm $adj_size)
    echo "$result,$name,$(( $i+1 ))" >> "$OUTPUT"

    sleep 1

  done
done

echo "Done! Results saved to $OUTPUT"
