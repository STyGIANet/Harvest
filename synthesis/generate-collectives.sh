#!/bin/bash


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_DIR=$SCRIPT_DIR/collectives
if [[ ! -d $DUMP_DIR ]];then
	mkdir -p $DUMP_DIR
fi

# Few examples:
# python3 generate-collective.py 4x4 67108864 4 reduce-scatter-rd-nd out.json
# python3 generate-collective.py 27 81 bruckallgather-r3-p3 out.json
# python3 generate-collective.py 8 67108864 binomial-broadcast out.json
# python3 generate-collective.py 4x4 67108864 1 reduce-scatter-swing-nd out.json
# python3 generate-collective.py 4x4 67108864 4 reduce-scatter-swing-nd out.json

# This is non-standard in the literature, and depends on specific hardware and software
ALPHAS=(10 100 500 1000 5000 10000)
# Ethernet generations, and NVLink 1.0 to 5.0 generations
BANDWIDTHS=(100 200 400 800 640 1200 2400 3600 7200)
# 10ns e.g., Sirius, or some opto-electrical lithium niobate switches in the range 10 to 300ns
# 10us e.g., Rotornet
# 1ms and beyond e.g., 3-D MEMS
ALPHARS=(10 50 100 300 500 1000 5000 10000 50000 100000 500000 1000000 10000000 100000000 1000000000)
# Can widely vary based on the system design, hop processing delays, and even cable lengths
DELTAS=(10 50 100 300 500 1000 5000 10000)

MESSAGE_SIZES=(1024 2048 4096 8192 16384 32768 65536 131072 262144 524288 1048576 \
2097152 4194304 8388608 16777216 33554432 67108864 134217728 268435456 536870912 1073741824)

MESSAGE_NAMES=(1KB 2KB 4KB 8KB 16KB 32KB 64KB 128KB 256KB 512KB 1MB 2MB 4MB 8MB 16MB 32MB \
64MB 128MB 256MB 512MB 1GB)


# What changes in the collective file: Message size, Number of nodes, Ports (or dimensions)
# Alpha, and other parameters are input to the topology synthesis, not for the collective itself

############# 1D AllReduce #############

NODES=(4 8 16 32 64 128 256)
PORTS=(1 2)
ALGS=(all-reduce-rd-nd all-reduce-swing-nd)

echo "Generating 1D AllReduce"

for N in ${NODES[@]};do
	for P in ${PORTS[@]};do
		for ALG in ${ALGS[@]};do
			for IDX in ${!MESSAGE_SIZES[@]};do
				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
				python3 generate-collective.py $N $MESSAGE_SIZE $P $ALG $OUTFILE
			done
		done
	done
done

############# All-to-All #############

NODES=(8 16 32 64)
PORTS=(1 2 3 4 8)
ALGS=(all-to-all-nd direct-all-to-all)

echo "Generating All to All"

for N in ${NODES[@]};do
	for P in ${PORTS[@]};do
		for ALG in ${ALGS[@]};do
			for IDX in ${!MESSAGE_SIZES[@]};do
				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
				python3 generate-collective.py $N $MESSAGE_SIZE $P $ALG $OUTFILE
			done
		done
	done
done

############# Bruck's #############

echo "Generating Bruck's r2"

ALGS=(bruckallgather-r2 bruckalltoall-r2)
NODES=(4 8 16 32 64)
PORTS=(1)
for N in ${NODES[@]};do
	for P in ${PORTS[@]};do
		for ALG in ${ALGS[@]};do
			for IDX in ${!MESSAGE_SIZES[@]};do
				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
				python3 generate-collective.py $N $MESSAGE_SIZE $ALG-p$P $OUTFILE
			done
		done
	done
done

echo "Generating Bruck's r4"

ALGS=(bruckallgather-r4 bruckalltoall-r4)
NODES=(4 16 64)
PORTS=(4)
for N in ${NODES[@]};do
	for P in ${PORTS[@]};do
		for ALG in ${ALGS[@]};do
			for IDX in ${!MESSAGE_SIZES[@]};do
				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
				python3 generate-collective.py $N $MESSAGE_SIZE $ALG-p$P $OUTFILE
			done
		done
	done
done

############# 2D AllReduce #############

echo "Generating 2D AllReduce"

DIMS=(4x4 8x4 16x4 8x8 16x8)
PORTS=(4)
ALGS=(all-reduce-rd-nd all-reduce-swing-nd)

for N in ${DIMS[@]};do
	for P in ${PORTS[@]};do
		for ALG in ${ALGS[@]};do
			for IDX in ${!MESSAGE_SIZES[@]};do
				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
				python3 generate-collective.py $N $MESSAGE_SIZE $P $ALG $OUTFILE
			done
		done
	done
done

############# 3D AllReduce #############

echo "Generating 3D AllReduce"

DIMS=(4x4x4 8x4x2 16x2x2)
PORTS=(6)
ALGS=(all-reduce-rd-nd all-reduce-swing-nd)

for N in ${DIMS[@]};do
	for P in ${PORTS[@]};do
		for ALG in ${ALGS[@]};do
			for IDX in ${!MESSAGE_SIZES[@]};do
				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
				python3 generate-collective.py $N $MESSAGE_SIZE $P $ALG $OUTFILE
			done
		done
	done
done

############# Broadcast #############

echo "Generating Broadcast"

NODES=(4 8 16 32 64)
PORTS=(1)
ALGS=(binomial-broadcast binary-broadcast)

for N in ${NODES[@]};do
	for P in ${PORTS[@]};do
		for ALG in ${ALGS[@]};do
			for IDX in ${!MESSAGE_SIZES[@]};do
				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
				python3 generate-collective.py $N $MESSAGE_SIZE $ALG $OUTFILE
			done
		done
	done
done