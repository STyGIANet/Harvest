import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import matplotlib.ticker as mticker
import pandas as pd
import matplotlib
import seaborn as sns
import os
from matplotlib.colors import LogNorm
from matplotlib.ticker import FormatStrFormatter
#%%

scriptdir = os.path.dirname(os.path.abspath(__file__))
plotsdir = os.environ.get("PLOTS_DIR", os.path.join(scriptdir, "plots"))
os.makedirs(plotsdir, exist_ok=True)
plotsdir = os.path.join(plotsdir, "")

filename = os.path.join(scriptdir, "alpha-beta.csv")
raw = np.loadtxt(filename, delimiter=",", skiprows=1, usecols=(0,1))
#%%
sizes = raw[:,0]
times_ms = raw[:,1]

grouped = defaultdict(list)
for s, t in zip(sizes, times_ms):
    grouped[int(s)].append(t)

sizes_unique = []
times_avg = []

for s in sorted(grouped.keys()):
    sizes_unique.append(s)
    times_avg.append(np.mean(grouped[s]))

sizes_unique = np.array(sizes_unique)
times_avg = np.array(times_avg)
times_s = times_avg / 1000.0

plateau_mask = sizes_unique <= 8 * 1024
alpha = np.mean(times_s[plateau_mask])

linear_mask = sizes_unique >= 4 * 1024 * 1024

sizes_linear = sizes_unique[linear_mask]
times_linear = times_s[linear_mask]

times_linear_adjusted = times_linear - alpha

beta = np.dot(sizes_linear, times_linear_adjusted) / np.dot(sizes_linear, sizes_linear)


pred_linear = alpha + beta * sizes_linear

ss_res = np.sum((times_linear - pred_linear)**2)
ss_tot = np.sum((times_linear - np.mean(times_linear))**2)
r2 = 1 - ss_res/ss_tot

bandwidth_Bps = 1 / beta
bandwidth_Gbps = bandwidth_Bps * 8 / 1e9

print("\n Alpha-Beta Analysis \n")
print(f"Alpha = {alpha*1e6:.2f} µs")
print(f"Beta = {beta:.3e} sec/byte")
print(f"Effective bandwidth = {bandwidth_Gbps:.2f} Gbps")
print(f"R^2 (coefficient of determination) = {r2:.5f}")


sizes_fit = np.linspace(min(sizes_unique), max(sizes_unique), 400)
times_fit = alpha + beta * sizes_fit

matplotlib.rcParams.update({'font.size': 22})

fig,ax = plt.subplots(1,1,figsize=(10, 4))
ax.scatter(sizes_unique/1e6, times_avg, label="Measured", zorder=3, marker='X',s=200)
ax.plot(sizes_fit/1e6, times_fit*1000,
         color="red", label=r'$\alpha-\beta$ model', lw=4)


# ax.axhline(alpha*1000, linestyle="--", color="green", label="Latency plateau")

ax.set_xlabel("Message Size (MB)")
ax.set_ylabel("Compl. time (ms)")
# ax.set_title("Latency vs Message Size (Alpha-Beta Model)")

def fmt_bytes(n):
    n = float(n)
    if n < 1024:
        return f"{n:.0f} B"
    if n < 1024**2:
        return f"{n/1024:.0f} KB"
    if n < 1024**3:
        return f"{n/1024**2:.0f} MB"
    return f"{n/1024**3:.0f} GB"

ax.set_xscale('log')
base_labels=sizes_unique[::8]
ax.set_xticks(sizes_unique[::8]/1e6)
ax.set_xticklabels(
    [fmt_bytes(base_labels[i]) for i in range(len(base_labels))],
    rotation=30
)
ax.legend()
ax.grid(True)
fig.tight_layout()
fig.show()
fig.savefig(plotsdir+'alpha-beta.pdf')
#%%

effective_bw = sizes_unique / times_s
effective_bw_gbps = effective_bw * 8 / 1e9

fig, ax = plt.subplots(1,1,figsize=(10, 8))
ax.plot(sizes_unique/1e6, effective_bw_gbps, marker="o",lw=3,markersize=20)

ax.set_xlabel("Message Size (MB)")
ax.set_ylabel("Effective Bandwidth (Gbps)")
ax.grid(True)
fig.tight_layout()
fig.savefig(plotsdir+'bandwidth-measurement.pdf')
#%%

residuals = times_linear - pred_linear

plt.figure(figsize=(8,6))
plt.scatter(sizes_linear/1e6, residuals*1e6)
plt.axhline(0, color="black")

plt.xlabel("Message Size (MB)")
plt.ylabel("Residual (µs)")
plt.title("Residuals of Alpha-Beta Model")
plt.grid(True)
plt.tight_layout()
plt.show()

#%%

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.colors as mcolors

df = pd.read_csv(os.path.join(scriptdir, "static_results.csv"))

g = (
    df.groupby(["BaseSize", "PermIndex", "Shift"], as_index=False)["FullTime"]
      .mean()
      .rename(columns={"FullTime": "T"})
)

tab = g.pivot(index="BaseSize", columns=["PermIndex", "Shift"], values="T").sort_index()

def col(perm, shift):
    return tab[(perm, shift)]

T11 = col(1, 1)
T12 = col(1, 2)
T13 = col(1, 3)
T22 = col(2, 2)
T33 = col(3, 3)
T23 = col(2, 3)

needed = [T11, T12, T13, T22, T33, T23]
mask = np.logical_and.reduce([~s.isna().to_numpy() for s in needed])

base_sizes = tab.index.to_numpy()[mask]
T11v = T11.to_numpy()[mask]
T12v = T12.to_numpy()[mask]
T13v = T13.to_numpy()[mask]
T22v = T22.to_numpy()[mask]
T33v = T33.to_numpy()[mask]
T23v = T23.to_numpy()[mask]

LOW  = 1 * 1024 * 1024 / 64 # 256 KB
HIGH = 4 * 1024 * 1024 * 1024 # 128 MB

size_mask = (base_sizes >= LOW) & (base_sizes <= HIGH)

base_sizes = base_sizes[size_mask]

T11v = T11v[size_mask]
T12v = T12v[size_mask]
T13v = T13v[size_mask]
T22v = T22v[size_mask]
T33v = T33v[size_mask]
T23v = T23v[size_mask]


alpha_r_values = np.logspace(-3, 1, 10)

BvN_ratio    = np.zeros((len(base_sizes), len(alpha_r_values)))
Static_ratio = np.zeros_like(BvN_ratio)
Min_ratio    = np.zeros_like(BvN_ratio)
ring_ratio   = np.zeros_like(BvN_ratio)
bestMinWithRing_ratio = np.zeros_like(BvN_ratio)

for i in range(len(base_sizes)):

    BvN_base    = T11v[i] + T12v[i] + T13v[i]
    Static_base = T11v[i] + T22v[i] + T33v[i]
    Middle_base = T11v[i] + T12v[i] + T23v[i]
    ring_base = T13v[i]*7

    for j, alpha_r in enumerate(alpha_r_values):
        BvN    = BvN_base + 2.0 * alpha_r
        Static = Static_base
        Ring   = ring_base
        Middle = Middle_base + alpha_r
        Harvest = min(BvN, Static, Middle)
        Best = min(Static, Ring)

        BvN_ratio[i, j]    = BvN / Harvest
        Static_ratio[i, j] = Static / Harvest
        ring_ratio[i,j]    = Ring / Harvest
        Min_ratio[i, j]    = min(BvN, Static) / Harvest
        bestMinWithRing_ratio[i, j] = Best / Harvest

def fmt_bytes(n):
    n = float(n)
    if n < 1024:
        return f"{n:.0f} B"
    if n < 1024**2:
        return f"{n/1024:.0f} KB"
    if n < 1024**3:
        return f"{n/1024**2:.0f} MB"
    return f"{n/1024**3:.0f} GB"


def adaptive_colorbar_ticks(vmin, vmax):
    ratio = vmax / vmin

    if vmax <= 2:
        ticks = np.linspace(1.0, vmax, 6)
        labels = [f"{t:.2f}" for t in ticks]

    elif vmax <= 3.2:
        ticks = np.arange(1, int(np.floor(vmax)) + 1)
        labels = [f"{int(t)}" for t in ticks]

    else:
        exponents = np.arange(
            int(np.floor(np.log10(vmin))),
            int(np.ceil(np.log10(vmax))) + 1
        )

        ticks = []
        for e in exponents:
            for m in [1, 2, 5]:
                val = m * (10 ** e)
                if vmin <= val <= vmax:
                    ticks.append(val)

        ticks = np.array(ticks)
        labels = [f"{t:.0f}" if t >= 10 else f"{t:.1f}" for t in ticks]

    return ticks, labels



def set_log_colorbar_one_decimal(hm, vmin, vmax):
    
    cbar = hm.collections[0].colorbar
    # ticks = nice_log_ticks(vmin, vmax)
    ticks, labels = adaptive_colorbar_ticks(vmin, vmax)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels(labels)
    cbar.ax.minorticks_off()


    
    # if ticks.size == 0:
    #     ticks = np.array([vmin, vmax])

    # cbar.set_ticks(ticks)
    # cbar.set_ticklabels([f"{t:.1f}" for t in ticks])
    
    # cbar.ax.minorticks_off()


def plot_heatmap(matrix, title, name):
    matplotlib.rcParams.update({'font.size': 32})
    fig, ax = plt.subplots(1,1 ,figsize=(10, 8))
    
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "CustomGrayMap",
        [
            (0.0, "white"),
            (0.01, "#d9d9d9"),
            (0.2, "#969696"),
            (1.0, "#252525")
        ]
    )
    
    mat = matrix
    vmin = 1.0
    vmax = np.nanmax(mat)
    ax = sns.heatmap(
        matrix,
        cmap=cmap,
        norm=LogNorm(vmin=1, vmax=vmax),
        cbar_kws={"label": title},
        xticklabels=False,
        yticklabels=False,
    )


    desired = np.array([0.001, 0.01, 0.1, 1.0, 10.0])
    
    xticks = [int(np.argmin(np.abs(alpha_r_values - v))) for v in desired]
    ax.set_xticks(xticks)
    
    ax.set_xticklabels([
        r"$1\,\mu s$",
        r"$10\,\mu s$",
        r"$100\,\mu s$",
        r"$1\,ms$",
        r"$10\,ms$"
    ],rotation=30)
    
    # set_log_colorbar_one_decimal(ax, vmin, vmax)

    yticks = np.arange(0, len(base_sizes), 4)

    if yticks[-1] != len(base_sizes) - 1:
        yticks = np.append(yticks, len(base_sizes) - 1)
    
    ax.set_yticks(yticks)
    ax.set_yticklabels(
        [fmt_bytes(base_sizes[i]) for i in yticks],
        rotation=25
    )

    ax.set_xlabel("Reconfiguration delay")
    ax.set_ylabel("Message Size")
    # ax.set_title(title)
    
    set_log_colorbar_one_decimal(ax, vmin, vmax)

    plt.tight_layout()
    plt.show()
    fig.savefig(plotsdir+name)
    

plot_heatmap(BvN_ratio, "BvN / Harvest","emu-bvn.pdf")
plot_heatmap(Static_ratio, "Static / Harvest","emu-static.pdf")
plot_heatmap(Min_ratio, "Best / Harvest","emu-best.pdf")
plot_heatmap(ring_ratio, "Ring / Harvest w/ RD","emu-ring.pdf")
plot_heatmap(1/ring_ratio, "Harvest w/ RD / Ring","emu-revring.pdf")
plot_heatmap(bestMinWithRing_ratio, "Best / Harvest w/ RD","emu-bestringrd.pdf")
