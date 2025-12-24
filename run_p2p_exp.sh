#!/bin/bash

# Compile the program
nvcc -arch=sm_70 -o p2p_thread_per_op p2p_thread_per_op.cu

# Path to your executable
EXEC="./p2p_thread_per_op"

# Output CSV file
OUTFILE="p2p_thread_per_op_gpu_times.csv"

# Write CSV header
echo "totalOperations,total_gpu_execution_time_ms" > "$OUTFILE"

# Loop over totalOperations from 2 to 1024 (powers of 2)
for totalOps in 2 4 8 16 32 64 128 256 512 1024; do
    for run in {1..10}; do
        # Run the program and capture output
        output=$($EXEC $totalOps)

        # Extract the line containing "Total GPU execution time:"
        time_line=$(echo "$output" | grep "Total GPU execution time:")

        # Extract the numeric time value in ms using awk
        time_ms=$(echo "$time_line" | awk '{print $5}')

        # Append to CSV
        echo "$totalOps,$time_ms" >> "$OUTFILE"
    done
done

echo "Results saved to $OUTFILE"
