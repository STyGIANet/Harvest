# Hardware emulation

This directory contains the NCCL/MPI microbenchmark and analysis used for the paper's 8-GPU hardware-emulation results. Each MPI rank controls one GPU. For a given permutation, every rank sends one chunk to its destination and receives one chunk from the rank mapped to it. Measurements for the distance-1, distance-2, and distance-4 permutations are combined to emulate the steps of Recursive Doubling schedules.

## Requirements

- Eight CUDA-capable GPUs reachable through MPI
- Eight network cards corresponding to eight GPUs (routing as described in the paper)
- CUDA and `nvcc`
- NCCL, with `NCCL_HOME` set to its installation directory
- An MPI implementation providing `mpicxx` and `mpirun`
- `nswrap`
	- This is a custom script we have on our servers that exports NCCL configuration and runs the rest of the bash command 
- Python with `numpy`, `pandas`, `matplotlib`, and `seaborn` for plotting

The `hostfile` describes the eight hosts. Replace its addresses, or set `HOSTFILE` to a different MPI hostfile. Set `NP` if the MPI process count is not eight; the experiment's permutations are written for eight ranks and must also be changed for another
size.

## Build

From this directory, run:

```bash
export NCCL_HOME=/path/to/nccl
./compile.sh
```
This creates `static_emu_new` executable.

## Collect measurements

Measure one-hop communication over the full message-size range for the
$\alpha$--$\beta$ fit:

```bash
./alpha-beta.sh
```

This writes `alpha-beta.csv`. Measure the three Recursive Doubling permutations and the chunk sizes needed by the emulated schedules with:

```bash
./run_emu.sh
```

This writes `static_results.csv`. Both drivers accept optional environment overrides:

```bash
HOSTFILE=/path/to/hostfile NP=8 ./run_emu.sh
```

The CSV files contain the measurements used for the paper, so copy them before rerunning an experiment if the original results must be retained. Times in these files are milliseconds.

## Generate plots

Run:

```bash
python3 plot.py
```

By default, the script reads `alpha-beta.csv` and `static_results.csv` from this directory and writes PDFs to `hardware-emulation/plots/`.

```bash
python3 plot.py
```

| Paper figure | Generated file | Description |
| --- | --- | --- |
| Figure 6(a) | `emu-bvn.pdf` | BvN schedule divided by Harvest |
| Figure 6(b) | `emu-static.pdf` | Static ring divided by Harvest |
| Figure 6(c) | `emu-best.pdf` | Best of BvN and static divided by Harvest |
| Figure 7 | `alpha-beta.pdf` | Measured one-hop time and the fitted $\alpha$--$\beta$ model |
| Figure 9(a) | `emu-bestringrd.pdf` | Best among Ring and RD divided by Harvest with RD |
| Figure 12(a) | `emu-ring.pdf` | Static Ring with RD divided by Harvest with RD |
| Figure 12(b) | `emu-revring.pdf` | Harvest with RD divided by static ring with ring algorithm |
| Figure 12(c) | `emu-bestringrd.pdf` | Best among static Ring with Ring/RD divided by Harvest with RD |

`plot.py` also generates `bandwidth-measurement.pdf`, which reports effective bandwidth but is not included in the paper. Figure 6(d), comes from the numerical synthesis workflow in `synthesis/plots-rd-emu-params.py`, not from this directory.

## Files

- `static_emu_new.cu`: NCCL permutation microbenchmark
- `compile.sh`: builds the benchmark
- `alpha-beta.sh`: collects one-hop calibration measurements
- `run_emu.sh`: collects Recursive Doubling permutation measurements
- `plot.py`: fits the cost model and creates the emulation plots
- `hostfile`: MPI hosts used by the original testbed
- `alpha-beta.csv`: cost model measurements used by the paper
- `static_results.csv`: schedule measurements used by the paper