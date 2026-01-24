from dataclasses import dataclass
from typing import List, Tuple
import math

Pair = Tuple[int, int, int]

# Note: Nodes are indexed from 0. Steps are indexed from 1.

@dataclass(frozen=True)
class PatternStep:
    id: int
    chunksize: int 
    demand: List[Pair]

def _parseDims(spec: str) -> List[int]:
    parts = spec.replace("x", ",").split(",")
    dims = [int(p) for p in parts if p.strip() != ""]
    if len(dims) == 0:
        raise ValueError("dims must be non-empty")
    return dims


################## Recursive Doubling (cyclic version)

def reduceScatterRecursiveDoubling(
    n: int,
    m: int,
) -> List[PatternStep]:
    if n <= 1 or (n & (n - 1)) != 0:
        raise ValueError("n must be a power of two and >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")

    s = n.bit_length() - 1
    # if m % (1 << s) != 0:
    #     raise ValueError("m must be divisible by n")

    steps: List[PatternStep] = []

    for i in range(1, s + 1):
        offset = 1 << (i - 1)
        chunk = m >> i
        demand: List[Pair] = []
        for u in range(n):
            v = (u + offset) % n
            demand.append((u, v, chunk))
        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))

    return steps


def allGatherRecursiveDoubling(
    n: int,
    m: int,
) -> List[PatternStep]:
    if n <= 1 or (n & (n - 1)) != 0:
        raise ValueError("n must be a power of two and >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")

    s = n.bit_length() - 1
    # if m % (1 << s) != 0:
    #     raise ValueError("m must be divisible by n")

    steps: List[PatternStep] = []

    for i in range(1, s + 1):
        offset = 1 << (s - i)
        chunk = m >> (s - i + 1)
        demand: List[Pair] = []
        for u in range(n):
            v = (u + offset) % n
            demand.append((u, v, chunk))
        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))

    return steps


def allReduceRecursiveDoubling(
    n: int,
    m: int,
) -> List[PatternStep]:
    rs = reduceScatterRecursiveDoubling(n, m)
    ag = allGatherRecursiveDoubling(n, m)

    steps: List[PatternStep] = []
    sid = 1

    for st in rs:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1

    for st in ag:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1

    return steps

################## Recursive Doubling (cyclic version, d-dimensional torus)

def _validateDimsPow2(dims: List[int]) -> None:
    if len(dims) < 1:
        raise ValueError("dims must be non-empty")
    for d in dims:
        if d <= 1 or (d & (d - 1)) != 0:
            raise ValueError("each dimension must be a power of two and >= 2")

def _rdDimScheduleStart(dims: List[int], start_dim: int) -> List[Tuple[int, int]]:
    _validateDimsPow2(dims)
    D = len(dims)
    start_dim %= D
    rem = [d.bit_length() - 1 for d in dims]
    used = [0] * D
    S = sum(rem)
    out: List[Tuple[int, int]] = []
    for t in range(S):
        dim = (start_dim + (t % D)) % D
        if rem[dim] == 0:
            k = 1
            while rem[(dim + k) % D] == 0:
                k += 1
            dim = (dim + k) % D
        e = used[dim]
        used[dim] += 1
        rem[dim] -= 1
        out.append((dim, e))
    return out

def reduceScatterRecursiveDoublingND(
    dims: List[int],
    m: int,
    ports: int,
) -> List[PatternStep]:
    _validateDimsPow2(dims)
    if m <= 0:
        raise ValueError("m must be > 0")
    if ports <= 0:
        raise ValueError("ports must be > 0")

    n = 1
    for d in dims:
        n *= d

    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")
    # if m % ports != 0:
    #     raise ValueError("m must be divisible by ports")

    mPerPort = m // ports
    # if mPerPort % n != 0:
    #     raise ValueError("m/ports must be divisible by n")

    D = len(dims)
    S = int(math.log2(n))

    scheds: List[List[Tuple[int, int]]] = []
    dirs: List[int] = []

    for p in range(ports):
        pm = p % (2 * D)
        start_dim = pm % D
        direction = 1 if pm < D else -1
        scheds.append(_rdDimScheduleStart(dims, start_dim))
        dirs.append(direction)

    steps: List[PatternStep] = []
    for t in range(1, S + 1):
        chunk = mPerPort >> t
        demand: List[Pair] = []
        for p in range(ports):
            dim, e = scheds[p][t - 1]
            off = (1 << e) * dirs[p]
            for u in range(n):
                c = _coordFromId(u, dims)
                c[dim] = _mod(c[dim] + off, dims[dim])
                v = _idFromCoord(c, dims)
                demand.append((u, v, chunk))
        steps.append(PatternStep(id=t, chunksize=chunk, demand=demand))
    return steps

def allGatherRecursiveDoublingND(
    dims: List[int],
    m: int,
    ports: int,
) -> List[PatternStep]:
    _validateDimsPow2(dims)
    if m <= 0:
        raise ValueError("m must be > 0")
    if ports <= 0:
        raise ValueError("ports must be > 0")

    n = 1
    for d in dims:
        n *= d

    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")
    # if m % ports != 0:
    #     raise ValueError("m must be divisible by ports")

    mPerPort = m // ports
    # if mPerPort % n != 0:
    #     raise ValueError("m/ports must be divisible by n")

    D = len(dims)
    S = int(math.log2(n))

    scheds: List[List[Tuple[int, int]]] = []
    dirs: List[int] = []

    for p in range(ports):
        pm = p % (2 * D)
        start_dim = pm % D
        direction = 1 if pm < D else -1
        scheds.append(_rdDimScheduleStart(dims, start_dim))
        dirs.append(direction)

    steps: List[PatternStep] = []
    for i in range(1, S + 1):
        chunk = mPerPort >> (S - i + 1)
        demand: List[Pair] = []
        for p in range(ports):
            dim, e = scheds[p][S - i]
            off = (1 << e) * dirs[p]
            for u in range(n):
                c = _coordFromId(u, dims)
                c[dim] = _mod(c[dim] + off, dims[dim])
                v = _idFromCoord(c, dims)
                demand.append((u, v, chunk))
        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))
    return steps

def allReduceRecursiveDoublingND(
    dims: List[int],
    m: int,
    ports: int,
) -> List[PatternStep]:
    rs = reduceScatterRecursiveDoublingND(dims, m, ports)
    ag = allGatherRecursiveDoublingND(dims, m, ports)
    steps: List[PatternStep] = []
    sid = 1
    for st in rs:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1
    for st in ag:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1
    return steps



############## Swing #######################

def _mod(a: int, b: int) -> int:
    r = a % b
    return r + b if r < 0 else r

def _rhoSwing(s: int) -> int:
    return (1 - ((-2) ** (s + 1))) // 3

def reduceScatterSwing1D(
    n: int,
    m: int,
) -> List[PatternStep]:
    if n <= 1 or (n & (n - 1)) != 0:
        raise ValueError("n must be a power of two and >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")

    s = n.bit_length() - 1
    # if m % (1 << s) != 0:
    #     raise ValueError("m must be divisible by n")

    steps: List[PatternStep] = []
    for i in range(1, s + 1):
        step0 = i - 1
        chunk = m >> i
        demand: List[Pair] = []
        for u in range(n):
            dist = _rhoSwing(step0)
            if (u & 1) == 1:
                dist *= -1
            v = _mod(u + dist, n)
            demand.append((u, v, chunk))
        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))
    return steps

def allGatherSwing1D(
    n: int,
    m: int,
) -> List[PatternStep]:
    if n <= 1 or (n & (n - 1)) != 0:
        raise ValueError("n must be a power of two and >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")

    s = n.bit_length() - 1
    # if m % (1 << s) != 0:
    #     raise ValueError("m must be divisible by n")

    steps: List[PatternStep] = []
    for i in range(1, s + 1):
        step0 = s - i
        chunk = m >> (s - i + 1)
        demand: List[Pair] = []
        for u in range(n):
            dist = _rhoSwing(step0)
            if (u & 1) == 1:
                dist *= -1
            v = _mod(u + dist, n)
            demand.append((u, v, chunk))
        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))
    return steps

def allReduceSwing1D(
    n: int,
    m: int,
) -> List[PatternStep]:
    rs = reduceScatterSwing1D(n, m)
    ag = allGatherSwing1D(n, m)

    steps: List[PatternStep] = []
    sid = 1
    for st in rs:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1
    for st in ag:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1
    return steps

def _coordFromId(rank: int, dims: List[int]) -> List[int]:
    coord = [0] * len(dims)
    nnodes = 1
    for d in dims:
        nnodes *= d
    x = rank
    for i in range(len(dims)):
        nnodes //= dims[i]
        coord[i] = x // nnodes
        x = x % nnodes
    return coord

def _idFromCoord(coord: List[int], dims: List[int]) -> int:
    rank = 0
    mult = 1
    for i in range(len(dims) - 1, -1, -1):
        c = coord[i]
        if c >= dims[i]:
            c = c % dims[i]
        elif c < 0:
            c = c % dims[i]
            if c:
                c = dims[i] + c
        rank += mult * c
        mult *= dims[i]
    return rank

def _swingDimSchedule(dims: List[int], port: int, S: int) -> List[Tuple[int, int]]:
    D = len(dims)
    term = [False] * D
    next_rel = [0] * D
    out: List[Tuple[int, int]] = []
    i = 0
    while i < S:
        o = 0
        while True:
            target_dim = (port + i + o) % D
            o += 1
            if not term[target_dim]:
                break

        rel = next_rel[target_dim]
        next_rel[target_dim] = rel + 1

        if rel >= math.ceil(math.log2(dims[target_dim])):
            term[target_dim] = True
            continue

        out.append((target_dim, rel))
        i += 1
    return out

def _peerSwing(rank: int, dims: List[int], dim: int, rel_step: int, port: int) -> int:
    coord = _coordFromId(rank, dims)
    dist = _rhoSwing(rel_step)
    if coord[dim] % 2:
        dist *= -1
    if port >= len(dims):
        dist *= -1
    coord[dim] = _mod(coord[dim] + dist, dims[dim])
    return _idFromCoord(coord, dims)

def _peersForPort(dims: List[int], port: int) -> List[List[int]]:
    n = 1
    for d in dims:
        n *= d
    S = math.ceil(math.log2(n))
    sched = _swingDimSchedule(dims, port, S)
    peers = [[0] * S for _ in range(n)]
    for u in range(n):
        for t in range(S):
            dim, rel = sched[t]
            peers[u][t] = _peerSwing(u, dims, dim, rel, port)
    return peers

def _computeBlocksBitmap(peers: List[List[int]], sender: int, step: int, bitmap: List[int]) -> None:
    S = len(peers[0])
    if step >= S:
        return
    for s in range(step, S):
        p = peers[sender][s]
        bitmap[p] = 1
        _computeBlocksBitmap(peers, p, s + 1, bitmap)

def _bitmapsForRank(peers: List[List[int]], rank: int) -> List[List[int]]:
    n = len(peers)
    S = len(peers[0])
    bitmaps = [[0] * n for _ in range(S)]
    reached_step = [S] * n
    for step in range(S):
        dest = peers[rank][step]
        bitmaps[step][dest] = 1
        _computeBlocksBitmap(peers, dest, step + 1, bitmaps[step])
        bitmaps[step][rank] = 0
        for i in range(n):
            if bitmaps[step][i]:
                if reached_step[i] != S:
                    prev = reached_step[i]
                    bitmaps[prev][i] = 0
                reached_step[i] = step
    return bitmaps

def reduceScatterSwingMultiportND(
    dims: List[int],
    m: int,
    ports: int,
) -> List[PatternStep]:
    if len(dims) < 1:
        raise ValueError("dims must be non-empty")
    if any(d <= 1 for d in dims):
        raise ValueError("each dimension must be >= 2")
    n = 1
    for d in dims:
        n *= d
    if m <= 0:
        raise ValueError("m must be > 0")
    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")
    if ports <= 0:
        raise ValueError("ports must be > 0")
    # if m % ports != 0:
    #     raise ValueError("m must be divisible by ports")

    S = math.ceil(math.log2(n))
    mPerPort = m // ports
    # if mPerPort % n != 0:
    #     raise ValueError("m/ports must be divisible by n")

    peersPorts: List[List[List[int]]] = []
    bitmapsPorts: List[List[List[List[int]]]] = []

    for p in range(ports):
        peers = _peersForPort(dims, p)
        peersPorts.append(peers)
        bm = [_bitmapsForRank(peers, r) for r in range(n)]
        bitmapsPorts.append(bm)

    steps: List[PatternStep] = []
    for t in range(S):
        demand: List[Pair] = []
        # assume same chunksize on all ports
        chunksize = 0
        for p in range(ports):
            peers = peersPorts[p]
            bm = bitmapsPorts[p]
            for u in range(n):
                v = peers[u][t]
                numBlocks = sum(bm[u][t])
                bytesSent = numBlocks * (mPerPort // n)
                if bytesSent:
                    demand.append((u, v, bytesSent))
                    chunksize=bytesSent
        steps.append(PatternStep(id=t + 1, chunksize=chunksize, demand=demand))
    return steps

def allGatherSwingMultiportND(
    dims: List[int],
    m: int,
    ports: int,
) -> List[PatternStep]:
    if len(dims) < 1:
        raise ValueError("dims must be non-empty")
    if any(d <= 1 for d in dims):
        raise ValueError("each dimension must be >= 2")
    n = 1
    for d in dims:
        n *= d
    if m <= 0:
        raise ValueError("m must be > 0")
    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")
    if ports <= 0:
        raise ValueError("ports must be > 0")
    # if m % ports != 0:
    #     raise ValueError("m must be divisible by ports")

    S = math.ceil(math.log2(n))
    mPerPort = m // ports
    # if mPerPort % n != 0:
    #     raise ValueError("m/ports must be divisible by n")

    peersPorts: List[List[List[int]]] = []
    bitmapsPorts: List[List[List[List[int]]]] = []

    for p in range(ports):
        peers = _peersForPort(dims, p)
        peersPorts.append(peers)
        bm = [_bitmapsForRank(peers, r) for r in range(n)]
        bitmapsPorts.append(bm)

    steps: List[PatternStep] = []
    for t in range(S):
        demand: List[Pair] = []
        idx = S - t - 1
        # assume same chunksize on all ports
        chunksize = 0
        for p in range(ports):
            peers = peersPorts[p]
            bm = bitmapsPorts[p]
            for u in range(n):
                v = peers[u][idx]
                numBlocks = sum(bm[v][idx])
                bytesSent = numBlocks * (mPerPort // n)
                if bytesSent:
                    demand.append((u, v, bytesSent))
                    chunksize=bytesSent
        steps.append(PatternStep(id=t + 1, chunksize=chunksize, demand=demand))
    return steps

def allReduceSwingMultiportND(
    dims: List[int],
    m: int,
    ports: int,
) -> List[PatternStep]:
    rs = reduceScatterSwingMultiportND(dims, m, ports)
    ag = allGatherSwingMultiportND(dims, m, ports)
    steps: List[PatternStep] = []
    sid = 1
    for st in rs:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1
    for st in ag:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1
    return steps

############ All-to-All

def allToAll(
    n: int,
    m: int,
) -> List[PatternStep]:
    if n <= 1:
        raise ValueError("n must be >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")
    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")

    chunk = m // n
    steps: List[PatternStep] = []

    for i in range(1, n):
        demand: List[Pair] = []
        for u in range(n):
            v = (u + i) % n
            demand.append((u, v, chunk))
        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))

    return steps

def allToAllNd(
    n: int,
    m: int,
    p: int,
) -> List[PatternStep]:
    if n <= 1:
        raise ValueError("n must be >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")
    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")

    chunk = m // n // p
    steps: List[PatternStep] = []

    for i in range(1, n):
        demand: List[Pair] = []
        for u in range(n):
            v = (u + i) % n
            dem = m // n
            demand.append((u, v, dem))
        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))

    return steps


def directAllToAll(
    n: int,
    m: int,
    p: int,
) -> List[PatternStep]:
    if n <= 1:
        raise ValueError("n must be >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")
    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")

    chunk = m // p
    steps: List[PatternStep] = []

    for i in range(1, 2):
        demand: List[Pair] = []
        for u in range(n):
            for v in range(n):
                if u==v:
                    continue
                demand.append((u, v, m // n))
        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))

    return steps


############# Binomial Tree Broadcast

def binomialTreeBroadcast(
    n: int,
    m: int,
    root: int = 0,
) -> List[PatternStep]:
    if n <= 1:
        raise ValueError("n must be >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")
    if not (0 <= root < n):
        raise ValueError("invalid root")

    steps: List[PatternStep] = []
    S = math.ceil(math.log2(n))

    for k in range(S):
        dist = 1 << k
        demand: List[Pair] = []

        for u in range(n):
            # translate to root-relative indexing
            ru = (u - root) % n
            if ru < dist:
                rv = ru + dist
                if rv < n:
                    v = (rv + root) % n
                    demand.append((u, v, m))

        steps.append(PatternStep(id=k + 1, chunksize=m, demand=demand))

    return steps

######################### Binary Tree Broadcast

def binaryTreeBroadcast(
    n: int,
    m: int,
    root: int = 0,
) -> List[PatternStep]:
    if n <= 1:
        raise ValueError("n must be >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")
    if not (0 <= root < n):
        raise ValueError("invalid root")

    steps: List[PatternStep] = []
    S = math.ceil(math.log2(n))

    for k in range(S):
        demand: List[Pair] = []
        start = 1 << k
        end = min(1 << (k + 1), n)

        for ru in range(start, end):
            u = (ru + root) % n
            left = 2 * ru + 1
            right = 2 * ru + 2

            if left < n:
                v = (left + root) % n
                demand.append((u, v, m))
            if right < n:
                v = (right + root) % n
                demand.append((u, v, m))

        if demand:
            steps.append(PatternStep(id=k + 1, chunksize=m, demand=demand))

    return steps

######################### Bruck's All-to-All

def bruckAllToAll(
    n: int,
    m: int,
    r: int,
    ports: int,
) -> List[PatternStep]:
    if n <= 1:
        raise ValueError("n must be >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")
    if r <= 1:
        raise ValueError("r must be >= 2")
    if ports <= 0:
        raise ValueError("ports must be > 0")
    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")

    # Require n = r^w (paper handles general n, but this keeps bytes uniform)
    w = 0
    tmp = 1
    while tmp < n:
        tmp *= r
        w += 1
    if tmp != n:
        raise ValueError("n must be a power of r for uniform Bruck index")

    # Each step sends ~ m / r bytes per rank
    bytes_per_step = m // r

    steps: List[PatternStep] = []
    sid = 1

    for x in range(w):
        base = r ** x
        z = 1
        while z <= r - 1:
            zs = list(range(z, min(r, z + ports)))
            demand: List[Pair] = []
            for u in range(n):
                for zz in zs:
                    v = (u + zz * base) % n
                    demand.append((u, v, bytes_per_step))
            steps.append(PatternStep(id=sid, chunksize=bytes_per_step, demand=demand))
            sid += 1
            z += ports

    return steps


###################### Bruck's concatenation (AllGather)

def bruckConcatenation(
    n: int,
    m: int,
    r: int,
    ports: int,
) -> List[PatternStep]:
    if n <= 1:
        raise ValueError("n must be >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")
    if r <= 1:
        raise ValueError("r must be >= 2")
    if ports <= 0:
        raise ValueError("ports must be > 0")
    # if m % n != 0:
    #     raise ValueError("m must be divisible by n")

    w = 0
    tmp = 1
    while tmp < n:
        tmp *= r
        w += 1
    if tmp != n:
        raise ValueError("n must be a power of r for uniform Bruck concat")

    block = m // n
    steps: List[PatternStep] = []
    sid = 1

    for x in range(w):
        base = r ** x
        payload = block * base
        z = 1
        while z <= r - 1:
            zs = list(range(z, min(r, z + ports)))
            demand: List[Pair] = []
            for u in range(n):
                for zz in zs:
                    v = (u + zz * base) % n
                    demand.append((u, v, payload))
            steps.append(PatternStep(id=sid, chunksize=payload, demand=demand))
            sid += 1
            z += ports

    return steps


################### Bine butterflies. This is same as swing really!
# Writing this just for completeness

def bineOffset(s: int, i: int) -> int:
    e = s - i + 1
    return (1 - ((-2) ** e)) // 3

def allGatherBine(
    n: int,
    m: int,
) -> List[PatternStep]:
    if n <= 1 or (n & (n - 1)) != 0:
        raise ValueError("n must be a power of two and >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")

    s = n.bit_length() - 1
    steps: List[PatternStep] = []

    for i in range(1, s + 1):
        chunk = m >> (s - i + 1)
        delta = bineOffset(s, i)

        demand: List[Pair] = []
        for r in range(n):
            if r % 2 == 0:
                q = (r + delta) % n
            else:
                q = (r - delta) % n
            demand.append((r, q, chunk))

        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))

    return steps

def reduceScatterBine(
    n: int,
    m: int,
) -> List[PatternStep]:
    if n <= 1 or (n & (n - 1)) != 0:
        raise ValueError("n must be a power of two and >= 2")
    if m <= 0:
        raise ValueError("m must be > 0")

    s = n.bit_length() - 1
    steps: List[PatternStep] = []

    for i in range(1, s + 1):
        chunk = m >> i
        delta = bineOffset(s, s - i + 1)

        demand: List[Pair] = []
        for r in range(n):
            if r % 2 == 0:
                q = (r + delta) % n
            else:
                q = (r - delta) % n
            demand.append((r, q, chunk))

        steps.append(PatternStep(id=i, chunksize=chunk, demand=demand))

    return steps

def allReduceBine(
    n: int,
    m: int,
) -> List[PatternStep]:
    rs = reduceScatterBine(n, m)
    ag = allGatherBine(n, m)

    steps: List[PatternStep] = []
    sid = 1

    for st in rs:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1

    for st in ag:
        steps.append(PatternStep(id=sid, chunksize=st.chunksize, demand=st.demand))
        sid += 1

    return steps
