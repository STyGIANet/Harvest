#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  3 23:22:33 2026

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

df = pd.read_csv("numerical-results.csv", delimiter=" ", usecols=[0, 1, 2, 3, 4, 5, 6, 7, 9, 10], names=[
                 "alg", "n", "ports", "msgname", "bw", "alpha", "delta", "alphar", "cost", "numreconfig"])

plotsdir="plots/"
os.makedirs(plotsdir, exist_ok=True)

# %%

MESSAGE_SIZES = [1024, 4096, 16384, 65536, 262144, 1048576,
    4194304, 16777216, 67108864, 268435456]
MESSAGE_NAMES = ["1KB", "4KB", "16KB", "64KB", "256KB",
    "1MB", "4MB", "16MB", "64MB", "256MB"]
ALPHARS = [10, 100, 1000, 10000, 100000, 1000000]
ALPHAR_NAMES = [r'$10$ns', r'$100$ns', r'$1\mu$s',
    r'$10\mu$s', r'$100\mu$s', r'$1$ms']


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

ALPHA = 500
DELTA = 500
STATIC = 100000000

NUM_PORTS = [1, 2, 3, 4, 8]
NODES = ["64", "32", "16", "8"]
# NUM_PORTS = [4]
# NODES = ["8"]

matplotlib.rcParams.update({'font.size': 36})

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        a2a = df[(df["alg"] == "all-to-all-nd") & (df["ports"] == PORTS) &
		          (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        
        arr = np.zeros((len(MESSAGE_NAMES),len(ALPHARS)))
        for i in range(len(MESSAGE_SIZES)):
            STATICCOST=list(a2a[(a2a["msgname"]==MESSAGE_NAMES[i])&(a2a["alphar"]==STATIC)]["cost"])
            if (len(STATICCOST)==0):
                continue
            STATICCOST=max(STATICCOST)
            for j in range(len(ALPHARS)):
                arr[i][j] = STATICCOST/a2a[(a2a["msgname"]==MESSAGE_NAMES[i])&(a2a["alphar"]==ALPHARS[j])]["cost"]
                # print(a2a[(a2a["msgname"]==MESSAGE_NAMES[i])&(a2a["alphar"]==ALPHARS[j])]["cost"])
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static-OPT / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(a2a["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')


#%%

ALPHA = 500
DELTA = 500
STATIC = 100000000

NUM_PORTS = [1, 2, 3, 4, 8]
NODES = ["64", "32", "16", "8"]
# NUM_PORTS = [4]
# NODES = ["8"]

matplotlib.rcParams.update({'font.size': 18})

cube = np.zeros((len(NUM_PORTS), len(MESSAGE_NAMES), len(ALPHARS)))

for pidx, PORTS in enumerate(NUM_PORTS):
    for N in NODES:
        if str(N) == str(PORTS):
            continue

        a2a = df[
            (df["alg"] == "all-to-all-nd") &
            (df["ports"] == PORTS) &
            (df["alpha"] == ALPHA) &
            (df["delta"] == DELTA) &
            (df["n"] == N)
        ]

        if a2a.empty:
            continue

        arr = np.zeros((len(MESSAGE_NAMES), len(ALPHARS)))

        for i in range(len(MESSAGE_NAMES)):
            static_rows = a2a[
                (a2a["msgname"] == MESSAGE_NAMES[i]) &
                (a2a["alphar"] == STATIC)
            ]["cost"]

            if static_rows.empty:
                continue

            STATICCOST = static_rows.max()

            for j in range(len(ALPHARS)):
                rows = a2a[
                    (a2a["msgname"] == MESSAGE_NAMES[i]) &
                    (a2a["alphar"] == ALPHARS[j])
                ]["cost"]

                if rows.empty:
                    continue

                arr[i, j] = STATICCOST / rows.iloc[0]

        cube[pidx] = arr
X, Y = np.meshgrid(range(len(ALPHARS)), range(len(MESSAGE_NAMES)))

fig = plt.figure(figsize=(14,10))
ax = fig.add_subplot(111, projection='3d')

cmap = cm.get_cmap("inferno", len(NUM_PORTS))
colors = [cmap(i) for i in range(len(NUM_PORTS))]

for pidx, PORTS in enumerate(NUM_PORTS):
    Z = cube[pidx]

    ax.plot_surface(
        X, Y, Z,
        alpha=0.6,
        color=colors[pidx]
    )

ax.set_xticks(range(len(ALPHARS)))
ax.set_xticklabels(ALPHAR_NAMES)
ax.set_yticks(range(len(MESSAGE_NAMES)))
ax.set_yticklabels(MESSAGE_NAMES,rotation=-20)

ax.set_xlabel("\n\nReconfiguration delay")
ax.set_ylabel("\n\n\nMessage size")
ax.set_zlabel("\nStatic / Harvest")
# fig.subplots_adjust(left=0.05, right=0.82, bottom=0.08, top=0.98)

# ax.set_box_aspect((2.5, 2.5, 2))
ax.view_init(elev=25, azim=-55)
# ax.dist = 2

handles = [
    Patch(facecolor=colors[pidx],label=f"Ports = {PORTS}", alpha=0.6)
    for pidx, PORTS in enumerate(NUM_PORTS)
]

ax.legend(
    handles=handles,
    loc='upper left',
    bbox_to_anchor=(0.02, 0.98)
)

# bbox = ax.get_tightbbox(fig.canvas.get_renderer()).expanded(1.02, 1.02)

# fig.tight_layout()
fig.savefig(plotsdir+"all-to-all-nd-3d.pdf",bbox_inches='tight',pad_inches=0.5)


#%%

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
#################################################################################################################################

ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [1]
NODES = ["64", "32", "16", "8"]

matplotlib.rcParams.update({'font.size': 36})

# Bruck allgather r2

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "bruckallgather-r2") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')


#%%
#################################################################################################################################

ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [1]
NODES = ["64", "32", "16", "8"]


# Bruck all to all r2

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "bruckalltoall-r2") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')


#%%
################################################################################################################################


ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [4]
NODES = ["64", "16", "4"]


# Bruck allgather r4

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "bruckallgather-r4") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=15)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=15)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=15)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

#%%
################################################################################################################################


ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [4]
NODES = ["64", "16", "4"]

# Bruck all to all r4

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "bruckalltoall-r4") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')


#%%
################################################################################################################################


ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [4]
NODES = ["4x4", "8x4", "16x4", "8x8"]
SIZES={}
SIZES["4x4"]=16
SIZES["8x4"]=32
SIZES["16x4"]=64
SIZES["8x8"]=64

# RD 2D

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "all-reduce-rd-nd") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
                arr1[i][j] = (BVNCOST+np.log2(int(SIZES[N]))*2*ALPHARS[j])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                arr2[i][j] = min([BVNCOST+np.log2(int(SIZES[N]))*2*ALPHARS[j], STATICCOST])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                print(arr1[i][j],ALPHARS[j])
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')


#%%
################################################################################################################################


ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [4]
NODES = ["4x4", "8x4", "16x4", "8x8"]
SIZES={}
SIZES["4x4"]=16
SIZES["8x4"]=32
SIZES["16x4"]=64
SIZES["8x8"]=64


# Swing 2d

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "all-reduce-swing-nd") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
                arr1[i][j] = (BVNCOST+np.log2(int(SIZES[N]))*2*ALPHARS[j])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                arr2[i][j] = min([BVNCOST+np.log2(int(SIZES[N]))*2*ALPHARS[j], STATICCOST])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                print(arr1[i][j],ALPHARS[j])
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

#%%
################################################################################################################################


ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [6]
NODES = ["4x4x4", "8x4x2", "16x2x2"]

# RD 3D

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "all-reduce-rd-nd") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
                arr1[i][j] = (BVNCOST+np.log2(int(64))*2*ALPHARS[j])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                arr2[i][j] = min([BVNCOST+np.log2(int(64))*2*ALPHARS[j], STATICCOST])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                print(arr1[i][j],ALPHARS[j])
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')


#%%
################################################################################################################################


ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [6]
NODES = ["4x4x4", "8x4x2", "16x2x2"]

# Swing 3d

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "all-reduce-swing-nd") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
                arr1[i][j] = (BVNCOST+np.log2(int(64))*2*ALPHARS[j])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                arr2[i][j] = min([BVNCOST+np.log2(int(64))*2*ALPHARS[j], STATICCOST])/dat[(dat["msgname"]==MESSAGE_NAMES[i])&(dat["alphar"]==ALPHARS[j])]["cost"]
                print(arr1[i][j],ALPHARS[j])
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

#%%
################################################################################################################################


ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [1]
NODES = ["4", "8", "16", "32", "64"]

# Binomial

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "binomial-broadcast") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')


#%%
################################################################################################################################


ALPHA = 500
DELTA = 500
STATIC = 100000000
BVN = 10

NUM_PORTS = [1]
NODES = ["4", "8", "16", "32", "64"]

# Binomial

for PORTS in NUM_PORTS:
    for N in NODES:
        if str(N) == str(PORTS):
            continue
        dat = df[(df["alg"] == "binary-broadcast") & (df["ports"] == PORTS) &
                  (df["alpha"] == ALPHA) & (df["delta"] == DELTA) & (df["n"] == N)]
        print(dat["numreconfig"])
        
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
        
        fig, ax = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax = sns.heatmap(arr, cmap=cmap, norm=norm, cbar_kws={'label': f'Static / Harvest'})
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax.set_title(f"N={N}, P={PORTS}")
        ax.set_xlabel("Reconfiguration delay")
        ax.set_ylabel("Message size")
        fig.tight_layout()
        fig.savefig(plotsdir+f'{list(dat["alg"])[0]}-static-{N}-{PORTS}.pdf')
        # ax.xaxis.grid(True,ls='--',c='lightgray')
        # ax.yaxis.grid(True,ls='--',c='lightgray')
        
        fig1, ax1 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr1)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.LogNorm(vmin=1, vmax=vmax)
        ax1 = sns.heatmap(arr1, cmap=cmap, norm=norm, cbar_kws={'label': f'BvN / Harvest'})
        cbar = ax1.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
        ax1.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax1.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax1.set_xlabel("Reconfiguration delay")
        ax1.set_ylabel("Message size")
        fig1.tight_layout()
        fig1.savefig(plotsdir+f'{list(dat["alg"])[0]}-BvN-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

        fig2, ax2 = plt.subplots(1,1,figsize=(10, 8))
        local_max = np.max(arr2)
        vmax = local_max if local_max > 1 else 1.05
        norm = mcolors.Normalize(vmin=1, vmax=vmax)
        ax2 = sns.heatmap(arr2, cmap=cmap, norm=norm, cbar_kws={'label': f'Best / Harvest'})
        cbar = ax2.collections[0].colorbar
        cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))
        ax2.set_xticklabels(ALPHAR_NAMES,rotation=45,ha='right')
        ax2.set_yticklabels(MESSAGE_NAMES,rotation=20)
        # ax1.set_title(f"N={N}, P={PORTS}")
        ax2.set_xlabel("Reconfiguration delay")
        ax2.set_ylabel("Message size")
        fig2.tight_layout()
        fig2.savefig(plotsdir+f'{list(dat["alg"])[0]}-Best-{N}-{PORTS}.pdf')
        # ax1.xaxis.grid(True,ls='--',c='lightgray')
        # ax1.yaxis.grid(True,ls='--',c='lightgray')

