# Reproducing Timing Experiments

This repository contains scripts and CUDA programs to reproduce the timing results reported for two key experiments:

1. **Synchronization Latency Experiment** (Master/Workers on two GPUs)
2. **Dynamic Programming Timing Experiment** (Harvest DP for recursive doubling)

The steps below describe how to run each experiment end-to-end, from compilation to figure generation.

---

## Prerequisites

Before running the experiments, please ensure:

* A machine with **at least two physical NVIDIA GPUs**
* NVIDIA driver and CUDA toolkit correctly installed and compatible
* CUDA is available in your environment (e.g., `nvcc --version` works)
* Python 3 with standard scientific packages (e.g., `numpy`, `pandas`, `matplotlib`)

All compilation steps are handled automatically by the provided bash scripts.

---

## Experiment 1: Synchronization Latency Experiment

This experiment measures **master/worker synchronization latency** on two physical GPUs.

* One GPU acts as a **master**
* The second GPU launches up to **256 logical workers (threads)**
* The number of logical workers is varied in **powers of two**

### What the experiment does

* For each logical worker count:

  * The experiment is repeated **10 times** (to capture variability)
  * Within each trial, the CUDA code performs **100 warm-up / steady-state repetitions**
  * The reported result is the **average latency in microseconds**
* This design ensures stable, steady-state timing measurements

### Step 1: Run the experiment

From the repository root, run:

```bash
./run_p2p_exp.sh
```

This script:

* Compiles the required CUDA program
* Runs the master/worker synchronization experiment
* Collects timing results across all configurations

### Output

After completion, the script generates the following CSV file:

```text
p2p_master_worker_times.csv
```

This file contains the synchronization latency results and serves as input to the plotting script.

### Step 2: Generate the figure

Run the Python plotting script:

```bash
python sync_latency_figure.py
```

### Result

The script generates the following figure in the same directory:

```text
figure3_synchronization_latency.pdf
```

---

## Experiment 2: Dynamic Programming Timing Experiment

This experiment measures the runtime of the **Harvest dynamic programming algorithm** for **1-D recursive doubling**.

### What the experiment does

* The CUDA implementation runs experiments for up to **1024 nodes**
* For each node count:

  * The experiment is repeated **10 times**
  * The resulting distribution is used to construct a **box plot**

### Step 1: Run the experiments

Execute the following script from the command line:

```bash
./dp_schedule_corrected_run_experiments.sh
```

This script:

* Compiles the dynamic programming CUDA code
* Executes the DP algorithm across all node counts
* Aggregates timing results across repeated trials

### Output

Upon completion, the script produces the following CSV file:

```text
dp_schedule_corrected_experiment_results.csv
```

This file contains all timing measurements required for plotting.

### Step 2: Generate the box plot

Run the Python plotting script:

```bash
python dp_schedule_plot_boxPlot.py
```

### Result

The script generates the final figure:

```text
dp_schedule_boxplot.pdf
```

---

## Notes

* All bash scripts are self-contained and handle compilation automatically
* If you modify CUDA versions or drivers, ensure consistency between `nvcc` and the runtime driver
* Generated CSV files can be reused to regenerate figures without rerunning experiments

---

If you encounter issues or want to extend these experiments (e.g., different GPU counts or repetition factors), the bash scripts are the best place to start.



