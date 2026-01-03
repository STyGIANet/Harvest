import pandas as pd
import matplotlib.pyplot as plt

# width of one LaTeX column in inches (from geometry & twocolumn)
COLUMN_WIDTH = 3.39  # ~8.6 cm

plt.rcParams.update({
    # figure size matching one column
    "figure.figsize": (COLUMN_WIDTH, COLUMN_WIDTH / 1.6),

    # --- fonts ---
    "font.size": 9.5,          # visually matches \footnotesize (8 pt) at column width
    "font.family": "serif",
    "font.serif": ["Libertine", "Times", "Times New Roman"],
    "mathtext.fontset": "cm",  # or 'stix' if you prefer mathptmx feel

    # --- use LaTeX for text rendering ---
    "text.usetex": True,
    "text.latex.preamble": r"""
        \usepackage{libertine}
        \usepackage{mathptmx}
        \usepackage[T1]{fontenc}
        \usepackage{amsmath, amssymb}
        \usepackage{microtype}
        \footnotesize
    """,

    # --- axis/legend sizes ---
    "axes.titlesize": 9.5,
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.5,

    # --- layout ---
    "figure.dpi": 300,
})

# Read the CSV file
df = pd.read_csv("p2p_master_worker_times.csv")

# Scale y-axis values by 10^6
# df["total_gpu_execution_time_us"] = df["total_gpu_execution_time_us"] * 1e6

# Restrict to domains up to 64 GPUs
df = df[df["totalOperations"] <= 1024]

# Create the boxplot
plt.figure(figsize=(8, 6))
df.boxplot(column="total_gpu_execution_time_us",
           by="totalOperations",
           grid=True)

# Labels and title
plt.xlabel("Number of GPUs")
plt.ylabel("Latency ("+r'$\mu$'+"s)")
plt.suptitle("")  # remove auto title
plt.title("")

# Save the figure as PDF
plt.tight_layout()
plt.savefig("figure3_synchronization_latency.pdf")

