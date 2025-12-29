import json
import sys
from typing import Tuple
from collectives import (
    reduceScatterRecursiveDoubling,
    allGatherRecursiveDoubling,
    allReduceRecursiveDoubling,
    reduceScatterRecursiveDoublingND,
    allGatherRecursiveDoublingND,
    allReduceRecursiveDoublingND,
    reduceScatterSwing1D,
    allGatherSwing1D,
    allReduceSwing1D,
    reduceScatterSwingMultiportND,
    allGatherSwingMultiportND,
    allReduceSwingMultiportND,
    allToAll,
    binomialTreeBroadcast,
    binaryTreeBroadcast,
    bruckAllToAll,
    bruckConcatenation,
    _parseDims,
)

def _parseBruck(spec: str) -> Tuple[int, int]:
    # quick and dirty parsing here. May be there is a better way
    # "bruck-r2-p4" is radix r=2, ports k=4.
    # The paper uses k notation. here we will use p sometimes.
    parts = spec.split("-")
    r = None
    p = None
    for part in parts:
        if part.startswith("r"):
            r = int(part[1:])
        elif part.startswith("p"):
            p = int(part[1:])
    if r is None or p is None:
        raise ValueError("bruck requires r and p (e.g., bruck-r2-p1)")
    return r, p

def main():
    if len(sys.argv) != 5 and len(sys.argv) != 6:
        raise SystemExit(
            "usage:\n"
            "  python3 generate-collective.py nodes messageSize collective out.json\n"
            "  python3 generate-collective.py dims messageSize numPorts collective out.json\n"
        )

    if len(sys.argv) == 5:
        n = int(sys.argv[1])
        m = int(sys.argv[2])
        collective = sys.argv[3]
        out = sys.argv[4]

        if collective == "reduce-scatter-rd":
            steps = reduceScatterRecursiveDoubling(n, m)
        elif collective == "all-gather-rd":
            steps = allGatherRecursiveDoubling(n, m)
        elif collective == "all-reduce-rd":
            steps = allReduceRecursiveDoubling(n, m)

        elif collective == "reduce-scatter-swing":
            steps = reduceScatterSwing1D(n, m)
        elif collective == "all-gather-swing":
            steps = allGatherSwing1D(n, m)
        elif collective == "all-reduce-swing":
            steps = allReduceSwing1D(n, m)

        elif collective == "all-to-all":
            steps = allToAll(n, m)

        elif collective == "binomial-broadcast":
            steps = binomialTreeBroadcast(n, m)

        elif collective == "binary-broadcast":
            steps = binaryTreeBroadcast(n, m)

        elif collective.startswith("bruckalltoall"):
            r, ports = _parseBruck(collective)
            steps = bruckAllToAll(n, m, r, ports)
        elif collective.startswith("bruckallgather"):
            r, ports = _parseBruck(collective)
            steps = bruckConcatenation(n, m, r, ports)

        else:
            raise ValueError(f"unknown collective: {collective}")

        doc = {
            "schema": "collective_pattern/v1",
            "collective": collective,
            "n": n,
            "units": "bytes",
            "steps": [
                {"id": s.id, "demand": [[u, v, c] for (u, v, c) in s.demand]}
                for s in steps
            ],
        }

    else:
        dims = _parseDims(sys.argv[1])
        m = int(sys.argv[2])
        ports = int(sys.argv[3])
        collective = sys.argv[4]
        out = sys.argv[5]

        n = 1
        for d in dims:
            n *= d

        if collective == "reduce-scatter-swing-nd":
            steps = reduceScatterSwingMultiportND(dims, m, ports)
        elif collective == "all-gather-swing-nd":
            steps = allGatherSwingMultiportND(dims, m, ports)
        elif collective == "all-reduce-swing-nd":
            steps = allReduceSwingMultiportND(dims, m, ports)

        elif collective == "reduce-scatter-rd-nd":
            steps = reduceScatterRecursiveDoublingND(dims, m, ports)
        elif collective == "all-gather-rd-nd":
            steps = allGatherRecursiveDoublingND(dims, m, ports)
        elif collective == "all-reduce-rd-nd":
            steps = allReduceRecursiveDoublingND(dims, m, ports)

        else:
            raise ValueError(f"unknown collective: {collective}")

        doc = {
            "schema": "collective_pattern/v1",
            "collective": collective,
            "n": n,
            "dims": dims,
            "ports": ports,
            "units": "bytes",
            "steps": [
                {"id": s.id, "demand": [[u, v, c] for (u, v, c) in s.demand]}
                for s in steps
            ],
        }

    with open(out, "w") as f:
        json.dump(doc, f, indent=2)

if __name__ == "__main__":
    main()
