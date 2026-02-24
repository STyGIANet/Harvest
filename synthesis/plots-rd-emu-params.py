#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  6 13:01:09 2026

@author: vamsi
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.ticker as mticker
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Patch
import matplotlib.cm as cm
import os
# %%

# format in the csv
# print(ALG,N,P,MESSAGE_NAME,BANDWIDTH,ALPHA,DELTA,ALPHA_R,RELAXATION,cost,num_of_reconfigs)

df = pd.read_csv("numerical-results-rd-emu-params.csv", delimiter=" ", usecols=[0, 1, 2, 3, 4, 5, 6, 7, 9, 10], names=[
                 "alg", "n", "ports", "msgname", "bw", "alpha", "delta", "alphar", "cost", "numreconfig"])

plotsdir='/home/vamsi/src/papers/harvest/sigcomm2026/plots/'
os.makedirs(plotsdir, exist_ok=True)

# %%

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


ALPHARS = [1000 , 10000 , 100000 , 1000000 , 100000000]
ALPHAR_NAMES = [r'$1\mu$s',
    r'$10\mu$s', r'$100\mu$s', r'$1$ms', r'$10$ms']


cmap = mcolors.LinearSegmentedColormap.from_list(
        "CustomGrayMap",
        [
            (0.0, "white"),
            (0.01, "#d9d9d9"),
            (0.2, "#969696"),
            (1.0, "#252525")
        ]
    )

#%%
ALPHA = 30320
DELTA = 1
STATIC = 100000000
BVN = 10

NUM_PORTS = [1]
NODES = [8]


matplotlib.rcParams.update({'font.size': 40})

# RD

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "reduce-scatter-rd-nd") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        # print(dat["numreconfig"])
        
        arr = np.zeros((len(MESSAGE_NAMES),len(ALPHARS)))
        arr1 = np.zeros((len(MESSAGE_NAMES),len(ALPHARS)))
        arr2 = np.zeros((len(MESSAGE_NAMES),len(ALPHARS)))
        
        for i in range(len(MESSAGE_SIZES)):
            STATICCOST=list(dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==STATIC)]["cost"])
            # print(STATICCOST)
            BVNCOST=list(dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==BVN)]["cost"])
            if (len(STATICCOST)==0):
                continue
            STATICCOST=max(STATICCOST)
            BVNCOST=max(BVNCOST)
            for j in range(len(ALPHARS)):
                arr[i][j] = STATICCOST/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                arr1[i][j] = (BVNCOST+np.log2(int(N))*2*ALPHARS[j])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                arr2[i][j] = min([BVNCOST+np.log2(int(N))*2*ALPHARS[j], STATICCOST])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                print(arr1[i][j],ALPHARS[j])
        
        fig, ax = plt.subplots(1,1,figsize=(12, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticks(np.arange(len(MESSAGE_NAMES))[::4])
        ax.set_yticklabels(MESSAGE_NAMES[::4],rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(12, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticks(np.arange(len(MESSAGE_NAMES))[::4])
        ax1.set_yticklabels(MESSAGE_NAMES[::4],rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(12, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticks(np.arange(len(MESSAGE_NAMES))[::4])
        ax2.set_yticklabels(MESSAGE_NAMES[::4],rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')
