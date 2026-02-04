#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  3 22:33:31 2026

@author: vamsi
"""

import numpy as np
import json
#%%

COLL_DIR="collectives/"
TOPO_DIR="topologies/"
DUMP_DIR="dump/"

ALPHAS=[10, 100, 500, 1000, 5000, 10000]
BANDWIDTHS=[100, 200, 400, 800, 640, 1200, 2400, 3600, 7200]
ALPHARS=[10, 100, 1000, 10000, 100000, 1000000, 100000000]
DELTAS=[10, 50, 100, 500, 1000, 5000, 10000]
MESSAGE_SIZES=[1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864, 268435456, 1073741824]
MESSAGE_NAMES=["1KB", "4KB", "16KB", "64KB", "256KB", "1MB", "4MB", "16MB", "64MB", "256MB", "1GB"]

LOGGING=0
RELAXATION=0

BANDWIDTHS=[800]
ALPHAS=[10, 10000, 500, 10000]
DELTAS=[10000, 10, 500, 10000]
RD=0


NODES=[64, 32, 16, 8]
PORTS=[2]
ALGS=["all-reduce-rd-nd", "all-reduce-swing-nd"]

for N in NODES:
	for BANDWIDTH in BANDWIDTHS:
		for ALPHA_DELTA_ID in range(len(ALPHAS)):
			ALPHA=ALPHAS[ALPHA_DELTA_ID]
			DELTA=DELTAS[ALPHA_DELTA_ID]
			for ALPHA_R in ALPHARS:
				for P in PORTS:
					for ALG in ALGS:
						for IDX in range(len(MESSAGE_SIZES)):

							MESSAGE_SIZE=MESSAGE_SIZES[IDX]
							MESSAGE_NAME=MESSAGE_NAMES[IDX]

							COLLECTIVE_FILE = COLL_DIR + f"collective-{ALG}-{N}-{P}-{MESSAGE_NAME}.json"
							OUTFILE= TOPO_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.json"
							DUMPFILE= DUMP_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.dump"
							
							with open(OUTFILE, "r") as f:
							    res = json.load(f)
							    cost = res["cost"]
							    num_of_reconfigs = res["num_of_reconfigs"]
							    print(ALG,N,P,MESSAGE_NAME,BANDWIDTH,ALPHA,DELTA,ALPHA_R,RELAXATION,cost,num_of_reconfigs)



PORTS=[1, 2, 3, 4, 8]
NODES=[64, 32, 16, 8]
ALGS=["all-to-all-nd", "direct-all-to-all"]

for N in NODES:
	for BANDWIDTH in BANDWIDTHS:
		for ALPHA_DELTA_ID in [2]:
			ALPHA=ALPHAS[ALPHA_DELTA_ID]
			DELTA=DELTAS[ALPHA_DELTA_ID]
			for ALPHA_R in ALPHARS:
				for P in PORTS:
					if N==P:
						continue
					for ALG in ALGS:
						for IDX in range(len(MESSAGE_SIZES)):

							MESSAGE_SIZE=MESSAGE_SIZES[IDX]
							MESSAGE_NAME=MESSAGE_NAMES[IDX]

							COLLECTIVE_FILE = COLL_DIR + f"collective-{ALG}-{N}-{P}-{MESSAGE_NAME}.json"
							OUTFILE= TOPO_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.json"
							DUMPFILE= DUMP_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.dump"
							
							with open(OUTFILE, "r") as f:
							    res = json.load(f)
							    cost = res["cost"]
							    num_of_reconfigs = res["num_of_reconfigs"]
							    print(ALG,N,P,MESSAGE_NAME,BANDWIDTH,ALPHA,DELTA,ALPHA_R,RELAXATION,cost,num_of_reconfigs)



PORTS=[1]
NODES=[4, 8, 16, 32, 64]
ALGS=["bruckallgather-r2", "bruckalltoall-r2"]

for N in NODES:
	for BANDWIDTH in BANDWIDTHS:
		for ALPHA_DELTA_ID in [2]:
			ALPHA=ALPHAS[ALPHA_DELTA_ID]
			DELTA=DELTAS[ALPHA_DELTA_ID]
			for ALPHA_R in ALPHARS:
				for P in PORTS:
					for ALG in ALGS:
						for IDX in range(len(MESSAGE_SIZES)):

							MESSAGE_SIZE=MESSAGE_SIZES[IDX]
							MESSAGE_NAME=MESSAGE_NAMES[IDX]

							COLLECTIVE_FILE = COLL_DIR + f"collective-{ALG}-{N}-{P}-{MESSAGE_NAME}.json"
							OUTFILE= TOPO_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.json"
							DUMPFILE= DUMP_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.dump"
							
							with open(OUTFILE, "r") as f:
							    res = json.load(f)
							    cost = res["cost"]
							    num_of_reconfigs = res["num_of_reconfigs"]
							    print(ALG,N,P,MESSAGE_NAME,BANDWIDTH,ALPHA,DELTA,ALPHA_R,RELAXATION,cost,num_of_reconfigs)



PORTS=[4]
NODES=[4, 16, 64]
ALGS=["bruckallgather-r4", "bruckalltoall-r4"]

for N in NODES:
	for BANDWIDTH in BANDWIDTHS:
		for ALPHA_DELTA_ID in [2]:
			ALPHA=ALPHAS[ALPHA_DELTA_ID]
			DELTA=DELTAS[ALPHA_DELTA_ID]
			for ALPHA_R in ALPHARS:
				for P in PORTS:
					for ALG in ALGS:
						for IDX in range(len(MESSAGE_SIZES)):

							MESSAGE_SIZE=MESSAGE_SIZES[IDX]
							MESSAGE_NAME=MESSAGE_NAMES[IDX]

							COLLECTIVE_FILE = COLL_DIR + f"collective-{ALG}-{N}-{P}-{MESSAGE_NAME}.json"
							OUTFILE= TOPO_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.json"
							DUMPFILE= DUMP_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.dump"
							
							with open(OUTFILE, "r") as f:
							    res = json.load(f)
							    cost = res["cost"]
							    num_of_reconfigs = res["num_of_reconfigs"]
							    print(ALG,N,P,MESSAGE_NAME,BANDWIDTH,ALPHA,DELTA,ALPHA_R,RELAXATION,cost,num_of_reconfigs)






PORTS=[4]
NODES=["4x4", "8x4", "16x4", "8x8"]
ALGS=["all-reduce-rd-nd", "all-reduce-swing-nd"]

for N in NODES:
	for BANDWIDTH in BANDWIDTHS:
		for ALPHA_DELTA_ID in [2]:
			ALPHA=ALPHAS[ALPHA_DELTA_ID]
			DELTA=DELTAS[ALPHA_DELTA_ID]
			for ALPHA_R in ALPHARS:
				for P in PORTS:
					for ALG in ALGS:
						for IDX in range(len(MESSAGE_SIZES)):

							MESSAGE_SIZE=MESSAGE_SIZES[IDX]
							MESSAGE_NAME=MESSAGE_NAMES[IDX]

							COLLECTIVE_FILE = COLL_DIR + f"collective-{ALG}-{N}-{P}-{MESSAGE_NAME}.json"
							OUTFILE= TOPO_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.json"
							DUMPFILE= DUMP_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.dump"
							
							with open(OUTFILE, "r") as f:
							    res = json.load(f)
							    cost = res["cost"]
							    num_of_reconfigs = res["num_of_reconfigs"]
							    print(ALG,N,P,MESSAGE_NAME,BANDWIDTH,ALPHA,DELTA,ALPHA_R,RELAXATION,cost,num_of_reconfigs)


PORTS=[6]
NODES=["4x4x4", "8x4x2", "16x2x2"]
ALGS=["all-reduce-rd-nd", "all-reduce-swing-nd"]

for N in NODES:
	for BANDWIDTH in BANDWIDTHS:
		for ALPHA_DELTA_ID in [2]:
			ALPHA=ALPHAS[ALPHA_DELTA_ID]
			DELTA=DELTAS[ALPHA_DELTA_ID]
			for ALPHA_R in ALPHARS:
				for P in PORTS:
					for ALG in ALGS:
						for IDX in range(len(MESSAGE_SIZES)):

							MESSAGE_SIZE=MESSAGE_SIZES[IDX]
							MESSAGE_NAME=MESSAGE_NAMES[IDX]

							COLLECTIVE_FILE = COLL_DIR + f"collective-{ALG}-{N}-{P}-{MESSAGE_NAME}.json"
							OUTFILE= TOPO_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.json"
							DUMPFILE= DUMP_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.dump"
							
							with open(OUTFILE, "r") as f:
							    res = json.load(f)
							    cost = res["cost"]
							    num_of_reconfigs = res["num_of_reconfigs"]
							    print(ALG,N,P,MESSAGE_NAME,BANDWIDTH,ALPHA,DELTA,ALPHA_R,RELAXATION,cost,num_of_reconfigs)



NODES=[4, 8, 16, 32, 64]
PORTS=[1]
ALGS=["binomial-broadcast", "binary-broadcast"]

for N in NODES:
	for BANDWIDTH in BANDWIDTHS:
		for ALPHA_DELTA_ID in [2]:
			ALPHA=ALPHAS[ALPHA_DELTA_ID]
			DELTA=DELTAS[ALPHA_DELTA_ID]
			for ALPHA_R in ALPHARS:
				for P in PORTS:
					for ALG in ALGS:
						for IDX in range(len(MESSAGE_SIZES)):

							MESSAGE_SIZE=MESSAGE_SIZES[IDX]
							MESSAGE_NAME=MESSAGE_NAMES[IDX]

							COLLECTIVE_FILE = COLL_DIR + f"collective-{ALG}-{N}-{P}-{MESSAGE_NAME}.json"
							OUTFILE= TOPO_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.json"
							DUMPFILE= DUMP_DIR + f"harvest-{ALG}-{N}-{P}-{MESSAGE_NAME}-{BANDWIDTH}-{ALPHA}-{DELTA}-{ALPHA_R}-{RELAXATION}.dump"
							
							with open(OUTFILE, "r") as f:
							    res = json.load(f)
							    cost = res["cost"]
							    num_of_reconfigs = res["num_of_reconfigs"]
							    print(ALG,N,P,MESSAGE_NAME,BANDWIDTH,ALPHA,DELTA,ALPHA_R,RELAXATION,cost,num_of_reconfigs)

