import json
import sys
from dataclasses import dataclass
from typing import List, Tuple
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
    allToAllNd,
    directAllToAll,
    binomialTreeBroadcast,
    binaryTreeBroadcast,
    bruckAllToAll,
    bruckConcatenation,
    reduceScatterBine,
    allGatherBine,
    allReduceBine,
    _parseDims,
)

Pair = Tuple[int, int, int]
@dataclass(frozen=True)
class PatternStepPost:
    id: int
    chunksize: int
    demand: List[Pair]

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

        ports = 1

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

        elif collective == "reduce-scatter-bine":
            steps = reduceScatterBine(n, m)

        elif collective == "all-gather-bine":
            steps = allGatherBine(n, m)

        elif collective == "all-reduce-bine":
            steps = allReduceBine(n, m)

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

        dims=[n]
        doc = {
            "schema": "collective_pattern/v1",
            "collective": collective,
            "n": n,
            "dims": dims,
            "ports": ports,
            "units": "bytes",
            "steps": [
                {"id": s.id, "chunksize":s.chunksize, "demand": [[u, v, c] for (u, v, c) in s.demand]}
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

        elif collective == "all-to-all-nd":
            steps = allToAllNd(n, m, ports)

        elif collective == "direct-all-to-all":
            steps = directAllToAll(n, m, ports)

        elif collective == "reduce-scatter-rd-nd":
            steps = reduceScatterRecursiveDoublingND(dims, m, ports)
        elif collective == "all-gather-rd-nd":
            steps = allGatherRecursiveDoublingND(dims, m, ports)
        elif collective == "all-reduce-rd-nd":
            steps = allReduceRecursiveDoublingND(dims, m, ports)

        else:
            raise ValueError(f"unknown collective: {collective}")


        # In case there are multiple ports send to the same destination, then merge then into single entry (add the size)
        coll: List(PatternStepPost) = []
        for s in steps:
            i = s.id
            chunksize = s.chunksize
            demand: Dict[Tuple[int,int], int] = {}
            for (u, v, c) in s.demand:
                if (u,v) in demand:
                    demand[(u,v)] += c
                else:
                    demand[(u,v)] = c
            demandList = [(u, v, c) for (u, v), c in demand.items()]
            coll.append(PatternStepPost(id=i, chunksize=chunksize, demand=demandList))

        # Note: The above loop merges multiple chunks to the same receiver.
        # chunksize in each step indicates the actual chunksize.
        # Entries in each step have a demand that can be a multiple of the chunksize, indicating multiple chunks to the same receiver
        doc = {
            "schema": "collective_pattern/v1",
            "collective": collective,
            "n": n,
            "dims": dims,
            "ports": ports,
            "units": "bytes",
            "steps": [
                {"id": s.id, "chunksize":s.chunksize, "demand": [[u, v, c] for (u, v, c) in s.demand]}
                for s in coll
            ],
        }

    with open(out, "w") as f:
        json.dump(doc, f, indent=2)

if __name__ == "__main__":
    main()
