#!/usr/bin/env python3
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



# Input CSV file
csv_file = "dp_schedule_corrected_experiment_results.csv"

# Load CSV into DataFrame
df = pd.read_csv(csv_file)

# Create boxplot grouped by "n"
plt.figure(figsize=(8, 6))
df.boxplot(column="timeMicro", by="n")
plt.title("")

# Labels and title
plt.xlabel("Number of GPUs (emulated)")
plt.ylabel("Compute time ("+r'$\mu$'+"s)")
plt.suptitle("")  # Removes the automatic "Boxplot grouped by n"

# Save plot to PDF
plt.tight_layout()
plt.savefig("dp_schedule_boxplot.pdf")

# Show plot
#plt.show()

