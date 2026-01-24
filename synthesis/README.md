
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

Many collectives can be generated in one-shot using `$ ./generate-collectives.sh`.

The general format is as follows:

```
python3 generate-collective.py nodes messageSize collective out.json # For 1-D collectives
python3 generate-collective.py dims messageSize numPorts collective out.json # For multi-dimensional collectives
```

Our repository currently supports the following collectives:

- Recursive doubling
	- reduce-scatter-rd
	- all-gather-rd
	- all-reduce-rd
- Swing
	- reduce-scatter-swing
	- all-gather-swing
	- all-reduce-swing
- Naive All-to-all
	- all-to-all
	- direct-all-to-all
- Binomial tree broadcast
	- binomial-broadcast
- Binary tree broadcast
	- binary-broadcast
- Bruck's All-to-all
	- bruckalltoall
- Bruck's AllGather
	- bruckallgather

reduce-scatter collective using recursive doubling algorithm, with 4x4 dimensions, message size 1024, with 4 ports at each node, and write to out.json:

```
python3 generate-collective.py 4x4 1024 4 reduce-scatter-rd-nd out.json
python3 generate-collective.py 8 4096 2 all-to-all-nd out.json # all to all, scales the size to k ports
python3 generate-collective.py 8 4096 2 direct-all-to-all out.json # send all at once, scales by k ports
```

For Bruck's algorithm, we use a special format to indicate the `r` and `p` parameters within the name.
```
python3 generate-collective.py 27 81 bruckallgather-r3-p3 out.json
```

# Synthesize Topology Schedules

To synthesize a topology schedule, we need a collective given as input in json format, the in-out degree for each node, link capacity (in Gbps), alpha_r (in nanoseconds), and path to output file.

```
python synthesize-schedule.py collective.json degree capacity alpha delta alpha_r logging relaxation simplify out.json
```

- `degree`: number of incoming and outgoing edges
- `capacity`: link bandwidth in Gbps
- `alpha`: setup latency (nanoseconds)
- `delta`: propagation delay (nanoseconds)
- `alpha_r`: reconfiguration delay (nanoseconds)
- `logging`: whether to log output from gurobi
- `relaxation`: Relaxes the edge variables to fractional, otherwise considered as integer variables
- `simplify`: This technique is optimal for recursive doubling, but can be used for other collectives as well. Essentially, the selection of topology for an interval (a,b) steps is based on step a's communication.