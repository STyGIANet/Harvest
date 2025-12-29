#!/bin/bash

# Output CSV file
OUTFILE="dp_schedule_results.csv"

# Write header
echo "S,n,k,m,GPU_DP_Time_ms,Total_Cost,Reconfig_Steps" > "$OUTFILE"

# Constant value of S
S=9

# Loop over n = 2, 4, ..., 1024
for n in 2 4 8 16 32 64 128 256 512 1024; do

    # Compute max_k = ceil(log2(n))
    max_k=$(echo "l($n)/l(2)" | bc -l)
    max_k=$(printf "%.0f\n" "$max_k")  # round to nearest int

    for ((k=1; k<=max_k; k++)); do
        for m in $(seq 10 10 500); do

            # Run the dp_schedule executable and capture the output
            output=$(./dp_schedule --n "$n" -k "$k" -m "$m" 2>/dev/null)

            # Skip if the run failed
            if [[ $? -ne 0 || -z "$output" ]]; then
                echo "Error running with n=$n, k=$k, m=$m"
                continue
            fi

            # Extract GPU DP Time
            gpu_time=$(echo "$output" | grep "GPU DP Time" | awk '{print $(NF-1)}')

            # Extract Minimum total cost
            total_cost=$(echo "$output" | grep "Minimum total cost" | awk '{print $NF}')

            # Extract optimal reconfig steps
            reconfig_line=$(echo "$output" | grep "Optimal reconfig steps")
            reconfig_steps=$(echo "$reconfig_line" | sed -E 's/.*\[([0-9, ]*)\].*/\1/' | tr -d ' ')

            # Write to CSV
            echo "$S,$n,$k,$m,$gpu_time,$total_cost,\"$reconfig_steps\"" >> "$OUTFILE"

        done
    done
done
