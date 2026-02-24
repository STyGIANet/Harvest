#!/bin/bash


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_DIR=$SCRIPT_DIR/manim
if [[ ! -d $DUMP_DIR ]];then
	mkdir -p $DUMP_DIR
fi

# Few examples:
# python3 generate-collective.py 4x4 67108864 4 reduce-scatter-rd-nd out.json
# python3 generate-collective.py 27 81 bruckallgather-r3-p3 out.json
# python3 generate-collective.py 8 67108864 binomial-broadcast out.json
# python3 generate-collective.py 4x4 67108864 1 reduce-scatter-swing-nd out.json
# python3 generate-collective.py 4x4 67108864 4 reduce-scatter-swing-nd out.json

MESSAGE_SIZES=(33554432)

MESSAGE_NAMES=(32MB)
############# 1D AllReduce #############

NODES=(8)
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

NODES=(8)
PORTS=(1 2)
ALGS=(all-gather-rd-nd all-gather-swing-nd)

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

NODES=(8)
PORTS=(1 2)
ALGS=(reduce-scatter-rd-nd reduce-scatter-swing-nd)

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

NODES=(8)
PORTS=(1)
ALGS=(all-to-all)

echo "Generating All to All 1D"

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

############# Bruck's #############

echo "Generating Bruck's r2"

ALGS=(bruckallgather-r2 bruckalltoall-r2)
NODES=(8)
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
NODES=(16)
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

DIMS=(4x4)
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

DIMS=(4x4x4)
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

NODES=(8 16)
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