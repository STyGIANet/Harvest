#!/bin/bash


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLL_DIR=$SCRIPT_DIR/collectives
TOPO_DIR=$SCRIPT_DIR/topologies
if [[ ! -d $TOPO_DIR ]];then
	mkdir -p $TOPO_DIR
fi

NUM_PARALLEL=$1

# In progress...

# Example:
# python synthesize-schedule.py collective.json degree capacity alpha delta alpha_r relaxation logging sched.json
# python synthesize-schedule.py collective.json 2 100 1 1 0 1 1 sched.json

# This is non-standard in the literature, and depends on specific hardware and software
ALPHAS=(10 100 500 1000 5000 10000)
# Ethernet generations, and NVLink 1.0 to 5.0 generations
BANDWIDTHS=(100 200 400 800 640 1200 2400 3600 7200)
# 10ns e.g., Sirius, or some opto-electrical lithium niobate switches in the range 10 to 300ns
# 10us e.g., Rotornet
# 1ms and beyond e.g., 3-D MEMS
ALPHARS=(10 100 1000 10000 100000 1000000 10000000)
# Can widely vary based on the system design, hop processing delays, and even cable lengths
DELTAS=(10 50 100 500 1000 5000 10000)

MESSAGE_SIZES=(1024 4096 16384 65536 262144 1048576 \
 4194304 16777216 67108864 268435456 1073741824)

MESSAGE_NAMES=(1KB 4KB 16KB 64KB 256KB 1MB 4MB 16MB \
64MB 256MB 1GB)

LOGGING=$2
RELAXATION=0
#####################################################################################################
# What changes in the collective file: Message size, Number of nodes, Ports (or dimensions)
# Alpha, and other parameters are input to the topology synthesis, not for the collective itself

# Too many experiments to iterate over every array
# Fix some configs

# Message size, Reconfiguration delay grid. 21 x 15 = 315 for say 4 combinations of alpha, delta. So 21 x 15 x 4 = 1260
# Fix the following four combinations
# alpha=10, delta=10000
# alpha=10000, delta=10
# alpha=100, delta=100
# alpha=10000, delta=10000

# Set bandwidth = 800Gbps throughout for now. Afterall, it is how alpha,delta change in relation to bw.
BANDWIDTHS=(800)
ALPHAS=(10 10000 100 10000)
DELTAS=(10000 10 100 10000)
#####################################################################################################
############# 1D AllGather #############

# NODES=(4 8 16 32 64 128)
NODES=(64 32 8 16)
PORTS=(2)
ALGS=(all-gather-rd-nd all-gather-swing-nd)

RD=0

cd $SCRIPT_DIR
./buildCpp.sh

echo "Generating 1D AllGather"
NUM_EXPS=0
for N in ${NODES[@]};do
	for BANDWIDTH in ${BANDWIDTHS[@]};do
		for ALPHA_DELTA_ID in ${!ALPHAS[@]};do
			ALPHA=${ALPHAS[$ALPHA_DELTA_ID]}
			DELTA=${DELTAS[$ALPHA_DELTA_ID]}
			for ALPHA_R in ${ALPHARS[@]};do
				for P in ${PORTS[@]};do
					for ALG in ${ALGS[@]};do
						if [[ $ALG == "all-gather-rd-nd" ]];then
							RD=0
						else
							RD=0
						fi
						for IDX in ${!MESSAGE_SIZES[@]};do
							MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
							MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
							COLLECTIVE_FILE=$COLL_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
							OUTFILE=$TOPO_DIR/topology-$ALG-$N-$P-$MESSAGE_NAME-$BANDWIDTH-$ALPHA-$DELTA-$ALPHA_R-$RELAXATION.json
							NUM_EXPS=$(( $NUM_EXPS + 1 ))
							while [[ $(ps aux | grep '/bin/bash ./synthesize-schedule' | wc -l) -gt $NUM_PARALLEL ]];do
								sleep 2
								echo "waiting at $NUM_EXPS..."
							done
							echo "synthesize-schedule $COLLECTIVE_FILE $P $BANDWIDTH $ALPHA $DELTA $ALPHA_R $LOGGING $RELAXATION $RD $OUTFILE"
							time (./synthesize-schedule $COLLECTIVE_FILE $P $BANDWIDTH $ALPHA $DELTA $ALPHA_R $LOGGING $RELAXATION $RD $OUTFILE; echo "################################"; echo $OUTFILE; echo "############################") &
							# exit
							# sleep 0.5
						done
					done
				done
			done
		done
	done
done

PORTS=(1)
NODES=(64 32 8 16)
# NODES=(64)
ALGS=(all-to-all)
for N in ${NODES[@]};do
	for BANDWIDTH in ${BANDWIDTHS[@]};do
		for ALPHA_DELTA_ID in ${!ALPHAS[@]};do
			ALPHA=${ALPHAS[$ALPHA_DELTA_ID]}
			DELTA=${DELTAS[$ALPHA_DELTA_ID]}
			for ALPHA_R in ${ALPHARS[@]};do
				for P in ${PORTS[@]};do
					for ALG in ${ALGS[@]};do
						if [[ $ALG == "all-gather-rd-nd" ]];then
							RD=0
						else
							RD=0
						fi
						for IDX in ${!MESSAGE_SIZES[@]};do
							MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
							MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
							COLLECTIVE_FILE=$COLL_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
							OUTFILE=$TOPO_DIR/topology-$ALG-$N-$P-$MESSAGE_NAME-$BANDWIDTH-$ALPHA-$DELTA-$ALPHA_R-$RELAXATION.json
							NUM_EXPS=$(( $NUM_EXPS + 1 ))
							while [[ $(ps aux | grep '/bin/bash ./synthesize-schedule' | wc -l) -gt $NUM_PARALLEL ]];do
								sleep 2
								echo "waiting at $NUM_EXPS..."
							done
							echo "synthesize-schedule $COLLECTIVE_FILE $P $BANDWIDTH $ALPHA $DELTA $ALPHA_R $LOGGING $RELAXATION $RD $OUTFILE"
							time (./synthesize-schedule $COLLECTIVE_FILE $P $BANDWIDTH $ALPHA $DELTA $ALPHA_R $LOGGING $RELAXATION $RD $OUTFILE; echo "################################"; echo $OUTFILE; echo "############################") &
							# exit
							# sleep 0.5
						done
					done
				done
			done
		done
	done
done

echo "Total $NUM_EXPS experiments"

############# Bruck's #############

# echo "Generating Bruck's r2"

# ALGS=(bruckallgather-r2 bruckalltoall-r2)
# NODES=(4 8 16 32 64 128)
# PORTS=(1 2)
# for N in ${NODES[@]};do
# 	for P in ${PORTS[@]};do
# 		for ALG in ${ALGS[@]};do
# 			for IDX in ${!MESSAGE_SIZES[@]};do
# 				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
# 				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
# 				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
# 				python3 generate-collective.py $N $MESSAGE_SIZE $ALG-p$P $OUTFILE
# 			done
# 		done
# 	done
# done

# echo "Generating Bruck's r4"

# ALGS=(bruckallgather-r4 bruckalltoall-r4)
# NODES=(4 16 64)
# PORTS=(1 2 4)
# for N in ${NODES[@]};do
# 	for P in ${PORTS[@]};do
# 		for ALG in ${ALGS[@]};do
# 			for IDX in ${!MESSAGE_SIZES[@]};do
# 				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
# 				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
# 				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
# 				python3 generate-collective.py $N $MESSAGE_SIZE $ALG-p$P $OUTFILE
# 			done
# 		done
# 	done
# done

# ############# 2D AllGather #############

# echo "Generating 2D AllGather"

# DIMS=(4x4 8x4 16x4 8x8 16x8)
# PORTS=(1 2 4)
# ALGS=(all-gather-rd-nd all-gather-swing-nd)

# for N in ${DIMS[@]};do
# 	for P in ${PORTS[@]};do
# 		for ALG in ${ALGS[@]};do
# 			for IDX in ${!MESSAGE_SIZES[@]};do
# 				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
# 				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
# 				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
# 				python3 generate-collective.py $N $MESSAGE_SIZE $P $ALG $OUTFILE
# 			done
# 		done
# 	done
# done

# ############# Broadcast #############

# echo "Generating Broadcast"

# NODES=(4 8 16 32 64 128)
# PORTS=(1)
# ALGS=(binomial-broadcast binary-broadcast)

# for N in ${NODES[@]};do
# 	for P in ${PORTS[@]};do
# 		for ALG in ${ALGS[@]};do
# 			for IDX in ${!MESSAGE_SIZES[@]};do
# 				MESSAGE_SIZE=${MESSAGE_SIZES[$IDX]}
# 				MESSAGE_NAME=${MESSAGE_NAMES[$IDX]}
# 				OUTFILE=$DUMP_DIR/collective-$ALG-$N-$P-$MESSAGE_NAME.json
# 				python3 generate-collective.py $N $MESSAGE_SIZE $ALG $OUTFILE
# 			done
# 		done
# 	done
# done