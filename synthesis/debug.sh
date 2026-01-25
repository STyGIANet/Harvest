#!/usr/bin/env bash

# Debugging which one crashed... Very annoying! Lol
declare -A pid2size
pids=()

cleanup() {
  echo "Crash detected: killing all remaining jobs"
  kill "${pids[@]}" 2>/dev/null || true
  exit 1
}
MESSAGE_SIZES=(1024 4096 16384 65536 262144 1048576  4194304 16777216 67108864 268435456 1073741824)
for i in "${MESSAGE_SIZES[@]}"; do
  echo "Running MESSAGE_SIZE=$i"

  python3 generate-collective.py 64 "$i" 1 all-to-all-nd out.json

  ./synthesize-schedule out.json 1 800 10 10000 10 0 0 0 "/tmp/sched$i.json" &

  pid=$!
  pid2size[$pid]=$i
  pids+=("$pid")
done

while ((${#pids[@]})); do
  if ! wait -n; then
    for pid in "${!pid2size[@]}"; do
      if ! kill -0 "$pid" 2>/dev/null; then
        echo "Crash at MESSAGE_SIZE=${pid2size[$pid]}"
        break
      fi
    done
    cleanup
  fi
done