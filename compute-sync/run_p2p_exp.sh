#!/bin/bash

# Compile the program
# nvcc -O3 -std=c++17 master_worker_p2p_plusWarmup.cu -o master_worker_p2p_plusWarmup
nvcc -O3 -std=c++17 -o master_worker_p2p_plusWarmup master_worker_p2p_plusWarmup.cu

# Path to your executable
EXEC="./master_worker_p2p_plusWarmup"

# Output CSV file
OUTFILE="p2p_master_worker_times.csv"

# Write CSV header
echo "totalOperations,total_gpu_execution_time_us" > "$OUTFILE"

# Loop over totalOperations from 2 to 1024 (powers of 2)
for totalOps in 2 4 8 16 32 64 128 256; do
    for run in {1..10}; do
        # Run the program and capture output
        output=$($EXEC $totalOps 100)

        # Extract the line containing "Total GPU execution time:"
        time_line=$(echo "$output" | grep "Avg per iteration:")

        # Extract the numeric time value in us using awk
        time_us=$(echo "$time_line" | awk -F'[()]' '{print $2}' | awk '{print $1}')

        # Append to CSV
        echo "$totalOps,$time_us" >> "$OUTFILE"
    done
done

echo "Results saved to $OUTFILE"
