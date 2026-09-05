
# Setup

The synthesis requires Gurobi software. It can be downloaded here: https://www.gurobi.com/downloads/gurobi-software/. The solver also requires a license. An academic license can be obtained for free on the website.

In our local directory, we have `gurobi1300`, and set the bash environment as follows. Edit `config.sh` file if your gurobi directory is located elsewhere. 

```
source config.sh
```

The following steps setup the python environment and install any dependencies

```
uv venv .venv
source .venv/bin/activate
uv pip install --upgrade pip
uv pip install -r requirements.txt
```

The c++ version requires json package installed:

```
sudo apt install nlohmann-json3-dev
```

# Generate collectives

Run the generator from the `synthesis` directory. It accepts one of two forms:

```text
python3 generate-collective.py <nodes> <message-size-bytes> <collective> <output.json>
python3 generate-collective.py <dimensions> <message-size-bytes> <ports> <collective> <output.json>
```

The first form generates a one-dimensional, single-port collective. The second form generates a multi-port collective; `<dimensions>` is either a node count such as `8` or an `x`-separated shape such as `4x4` or `4x4x4`. The total node
count written to the output is the product of the dimensions.

Supported one-dimensional collectives are:

- Recursive doubling: `reduce-scatter-rd`, `all-gather-rd`, `all-reduce-rd`
- Swing: `reduce-scatter-swing`, `all-gather-swing`, `all-reduce-swing`
- Bine: `reduce-scatter-bine`, `all-gather-bine`, `all-reduce-bine`
- All-to-all: `all-to-all`
- Broadcast: `binomial-broadcast`, `binary-broadcast`
- Bruck all-to-all: `bruckalltoall-r<R>-p<P>`
- Bruck all-gather: `bruckallgather-r<R>-p<P>`

Supported multi-port collectives are:

- Recursive doubling: `reduce-scatter-rd-nd`, `all-gather-rd-nd`, `all-reduce-rd-nd`
- Swing: `reduce-scatter-swing-nd`, `all-gather-swing-nd`, `all-reduce-swing-nd`
- All-to-all: `all-to-all-nd`, `direct-all-to-all`

For example:

```bash
# One-dimensional recursive-doubling all-reduce on 8 nodes
python3 generate-collective.py 8 4096 all-reduce-rd out.json

# Four-port recursive-doubling reduce-scatter on a 4x4 logical shape
python3 generate-collective.py 4x4 1024 4 reduce-scatter-rd-nd out.json

# Two-port all-to-all on 8 nodes
python3 generate-collective.py 8 4096 2 all-to-all-nd out.json

# Bruck all-gather on 27 nodes with radix 3 and 3 ports
python3 generate-collective.py 27 81 bruckallgather-r3-p3 out.json
```

In a Bruck collective name, `<R>` is the radix (at least 2) and `<P>` is the
number of ports (at least 1). Although the single-port command form is used,
the port count is read from the collective name and recorded in the output.

To generate the repository's full predefined set in parallel, run:

```bash
./generate-collectives.sh
```

The script uses up to `nproc` concurrent generator processes and writes the JSON files to `synthesis/collectives/`. The generated documents use the `collective_pattern/v1` schema and record dimensions, port count, byte units, and the communication demand for each step.

# Synthesize Topology Schedules

Build the C++ scheduler after configuring Gurobi:

```bash
source config.sh
./buildCpp.sh
```

The scheduler consumes a collective JSON file produced by `generate-collective.py` and has the following interface:

```bash
./synthesize-schedule <collective.json> <degree> <capacity-gbps> <alpha-ns> <delta-ns> <alpha-r-ns> <logging> <relaxation> <rd> <output.json>
```

- `collective.json`: input collective in the `collective_pattern/v1` format
- `degree`: number of links, or units of link capacity, available to each node
- `capacity-gbps`: capacity of one link in Gbps
- `alpha-ns`: per-step setup latency in nanoseconds
- `delta-ns`: propagation delay in nanoseconds
- `alpha-r-ns`: topology reconfiguration delay in nanoseconds
- `logging`: `1` enables Gurobi and scheduler logging; `0` disables it
- `relaxation`: retained for command-line compatibility; the current C++ scheduler accepts this value but does not use it (experimental, unused currently)
- `rd`: candidate-topology search mode. Use `0` for the full candidate set or `1` to restrict each interval to its first communication step and the unshifted base topology. The restricted mode is intended for recursive-doubling-style communication.
- `output.json`: destination for the synthesized schedule

For example, the following command synthesizes a degree-2 schedule over 100 Gbps links, with 10 ns setup latency, 50 ns propagation delay, and 1000 ns reconfiguration delay:

```bash
./synthesize-schedule collectives/collective-all-reduce-rd-nd-8-1-4KB.json \
  2 100 10 50 1000 0 0 1 out.json
```

The output contains the total `cost` in nanoseconds, the selected `num_of_reconfigs`, `reconf_cost_total`, `alpha_r`, and `collective`. Each entry in `steps` contains a 1-based collective step and a `topology` array. A topology
entry `[u, v, k]` assigns `k` directed links (or capacity units) from node `u` to node `v`. The same topology can appear in consecutive steps when no reconfiguration is selected between them.

`synthesize-schedule.py` provides a Python implementation with the same positional arguments, but the repository's experiment scripts build and invoke the C++ executable. To launch the predefined experiment sweep with a limit on concurrent scheduler processes, run:

```bash
./synthesize-schedules.sh <max-parallel-jobs>
```

The sweep reads collective files from `synthesis/collectives/`, writes schedule JSON files to `synthesis/topologies/`, and writes command output to `synthesis/dump/`. Its parameter arrays and enabled experiments are configured
directly in the script.

# Plots

The numerical-evaluation plots require `numpy`, `pandas`, `matplotlib`, and
`seaborn`. First, convert the synthesized topology JSON files into the
space-delimited results file consumed by the plotting script, then generate the
PDFs:

```bash
python3 parse-results.py > numerical-results.csv
python3 plots.py
```

`parse-results.py` reads from `synthesis/topologies/`. `plots.py` reads `numerical-results.csv` and writes its figures to `synthesis/plots/`.

The paper uses the following outputs from `plots.py` in its Numerical optimization figures:

| Paper figure | Generated file |
| --- | --- |
| Figure 8 | `plots/all-to-all-nd-3d.pdf` |
| Figure 14(a) | `plots/all-reduce-swing-nd-static-8x8-4.pdf` |
| Figure 14(b) | `plots/all-reduce-swing-nd-static-16x4-4.pdf` |
| Figure 14(c) | `plots/all-reduce-swing-nd-static-8x4x2-6.pdf` |
| Figure 14(d) | `plots/all-reduce-swing-nd-static-16x2x2-6.pdf` |
| Figure 14(e) | `plots/all-reduce-swing-nd-BvN-8x8-4.pdf` |
| Figure 14(f) | `plots/all-reduce-swing-nd-BvN-16x4-4.pdf` |
| Figure 14(g) | `plots/all-reduce-swing-nd-BvN-8x4x2-6.pdf` |
| Figure 14(h) | `plots/all-reduce-swing-nd-BvN-16x2x2-6.pdf` |
| Figure 14(i) | `plots/all-reduce-swing-nd-Best-8x8-4.pdf` |
| Figure 14(j) | `plots/all-reduce-swing-nd-Best-16x4-4.pdf` |
| Figure 14(k) | `plots/all-reduce-swing-nd-Best-8x4x2-6.pdf` |
| Figure 14(l) | `plots/all-reduce-swing-nd-Best-16x2x2-6.pdf` |
| Figure 15(a) | `plots/bruckalltoall-r4-static-64-4.pdf` |
| Figure 15(b) | `plots/bruckallgather-r4-static-64-4.pdf` |
| Figure 15(c) | `plots/binomial-broadcast-static-64-1.pdf` |
| Figure 15(d) | `plots/binary-broadcast-static-64-1.pdf` |
| Figure 15(e) | `plots/bruckalltoall-r4-BvN-64-4.pdf` |
| Figure 15(f) | `plots/bruckallgather-r4-BvN-64-4.pdf` |
| Figure 15(g) | `plots/binomial-broadcast-BvN-64-1.pdf` |
| Figure 15(h) | `plots/binary-broadcast-BvN-64-1.pdf` |
| Figure 15(i) | `plots/bruckalltoall-r4-Best-64-4.pdf` |
| Figure 15(j) | `plots/bruckallgather-r4-Best-64-4.pdf` |
| Figure 15(k) | `plots/binomial-broadcast-Best-64-1.pdf` |
| Figure 15(l) | `plots/binary-broadcast-Best-64-1.pdf` |

The baseline component of each filename describes the plotted speedup ratio: `static` compares the static topology with Harvest, `BvN` compares a schedule that reconfigures every step with Harvest, and `Best` compares the better of
those two baselines with Harvest.