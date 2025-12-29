#!/bin/bash

# Output CSV file
outfile="dp_schedule_corrected_experiment_results.csv"

# Number of runs
runs=10

# Program and arguments
cmd="./dp_schedule_corrected -n 8 -m 1000000 --delta 500 --bw 800 --reconf 1"

# Write CSV header
echo "n,timeMicro" > "$outfile"

# Run the program multiple times and extract n and timeMicro, excluding n=4
for i in $(seq 1 $runs); do
    $cmd | awk 'NR>1 && $1!=4 {print $1","$3}' >> "$outfile"
done

echo "Done. Results saved to $outfile"

