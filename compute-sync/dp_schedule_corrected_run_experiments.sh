#!/bin/bash
set -e  # Exit immediately if compilation or execution fails

# =========================
# Build step
# =========================
SRC="dp_schedule_corrected.cu"
BIN="dp_schedule_corrected"

echo "Compiling $SRC -> $BIN"
nvcc -O3 -use_fast_math -std=c++17 "$SRC" -o "$BIN"

# =========================
# Experiment configuration
# =========================

# Output CSV file
outfile="dp_schedule_corrected_experiment_results.csv"

# Number of runs
runs=10

# Program and arguments
cmd="./$BIN -n 8 -m 1000000 --delta 500 --bw 800 --reconf 1"

# =========================
# Run experiments
# =========================

# Write CSV header
echo "n,timeMicro" > "$outfile"

# Run the program multiple times and extract n and timeMicro, excluding n=4
for i in $(seq 1 $runs); do
    $cmd | awk 'NR>1 && $1!=4 {print $1","$3}' >> "$outfile"
done

echo "Done. Results saved to $outfile"

