# Harvest

This repository contains the code and scripts required to reproduce the simulation results presented in the **Harvest** paper.

The repository includes:

* Harvest topology synthesizer
* Harvest optical circuit switched network simulator built on top of ns3
* A collective synthesizer
* The ASTRA-sim distributed machine learning system simulator
* Scripts for reproducing paper results

## Requirements

#### Docker
Before starting, please make sure to install [Docker](https://docs.docker.com/engine/install/ubuntu/) on your machine.
#### Gurobi License Setup
Please also be sure to obtain a [Gurobi](https://www.gurobi.com/) license. The license is required to run the topology synthesizer.
We have used the free academic license for our experiments.

Please rename the license file to `gurobi.lic` and place it in the Harvest base directory before continuing.

##### Note on gurobi license:
If a Gurobi license cannot be obtained, you may comment out **lines 90–105** in the `Dockerfile`, which contain the Gurobi setup.

All required topology files are provided in:

```text
Harvest/astra-sim/acad/reconfigurable-topologies
```

Therefore, even without access to a Gurobi license, you can still run the simulations using the provided topology files.
## Repository Setup

Clone the repository along with its submodules:

```bash
git clone --recurse-submodules git@github.com:STyGIANet/Harvest.git
cd Harvest
```

Change the name of the directory:

```bash
mv astra-sim-dev astra-sim
```

Build the Docker image, then run the container with the current host directory mounted to Docker's internal /app directory.
```bash
docker build --no-cache -t harvest:latest -f Dockerfile .
docker run -it -v $(pwd):/app harvest:latest bash
```
Once you have started the Docker container, you can navigate to the individual folders to run the experiments described in our paper:

* `astra-sim` folder (main): Network simulation experiments corresponding to Figures 5 and 9(b).
* `synthesis`folder: Topology synthesis and numerical evaluation, including replication of Figure 8.
* `hardware-emulation` folder: Hardware experiment replication on an 8-GPU testbed, covering *Figures 6, 7, and 9(a).
* `compute-sync` folder: Synchronization experiments corresponding to Figures 10 and 11.

