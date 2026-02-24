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
MESSAGE_SIZES = [
    262144,
    393216, 524288, 786432,
    1048576, 1572864, 2097152,
    3145728, 4194304,
    6291456, 8388608,
    12582912, 16777216,
    25165824, 33554432,
    50331648, 67108864,
    100663296, 134217728,
    201326592, 268435456,
]

MESSAGE_NAMES = [
    "256KB",
    "384KB", "512KB", "768KB",
    "1MB", "1.5MB", "2MB",
    "3MB", "4MB",
    "6MB", "8MB",
    "12MB", "16MB",
    "24MB", "32MB",
    "48MB", "64MB",
    "96MB", "128MB",
    "192MB", "256MB",
]


LOGGING=0
RELAXATION=0

BANDWIDTHS=[85]
ALPHAS=[30320]
DELTAS=[1]
RD=0


NODES=[8]
PORTS=[1]
ALGS=["reduce-scatter-rd-nd"]

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
