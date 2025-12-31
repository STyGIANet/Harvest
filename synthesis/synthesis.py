from typing import List, Tuple, Dict
import math
import gurobipy as gp
from gurobipy import GRB

Pair = Tuple[int, int, int]
Topology = Dict[Tuple[int, int], int]


class DPScheduler:
    def __init__(
        self,
        steps: List[List[Pair]],
        num_nodes: int,
        d: int,
        c: float,
        beta: float,
        alpha_r: float,
    ):
        self.steps = steps
        self.s = len(steps)
        self.n = num_nodes
        self.d = d
        self.c = c
        self.beta = beta
        self.alpha_r = alpha_r
        self._cache: Dict[Tuple[int, int], Tuple[Topology, float]] = {}

    def completion_time(self, a: int, b: int) -> Tuple[Topology, float]:
        key = (a, b)
        if key in self._cache:
            return self._cache[key]

        model = gp.Model()
        model.Params.OutputFlag = 0

        x = {}
        for u in range(self.n):
            for v in range(self.n):
                if u != v:
                    # number of edges between u,v. This can also be interpreted as the capacity between u,v
                    x[u, v] = model.addVar(vtype=GRB.BINARY, lb=0)

        theta = {}
        T = {}
        f = {}

        for i in range(a, b + 1):
            # Concurrent flow theta variable
            # Lets give an epsilon for the lb, so that the inverse doesn't go to infinity
            theta[i] = model.addVar(lb=1e-6, ub=1)
            # auxiliary variable corresponding to the inverse of theta
            T[i] = model.addVar(lb=1e-6)
            for (s, t, _) in self.steps[i - 1]:
                # print("adding flow var for step", i-1)
                for u in range(self.n):
                    for v in range(self.n):
                        if u != v:
                            # flow variable for ith step, for demand s,t, traversing edge u,v
                            f[i, s, t, u, v] = model.addVar(lb=0)

        model.update()

        # Degree constraints
        for u in range(self.n):
            model.addConstr(gp.quicksum(x[u, v] for v in range(self.n) if u != v) <= self.d)
            model.addConstr(gp.quicksum(x[v, u] for v in range(self.n) if u != v) <= self.d)

        # Flow conservation and demand constraints
        for i in range(a, b + 1): # For each step between a, b (including)
            for (s, t, demand) in self.steps[i - 1]: # Note: steps are indexed from 1
                for u in range(self.n):
                    outflow = gp.quicksum(f[i, s, t, u, v] for v in range(self.n) if u != v)
                    inflow = gp.quicksum(f[i, s, t, v, u] for v in range(self.n) if u != v)
                    if u == s:
                        model.addConstr(outflow - inflow == theta[i] * demand)
                    elif u == t:
                        model.addConstr(outflow - inflow == -theta[i] * demand)
                    else:
                        model.addConstr(outflow - inflow == 0)

        # Capacity constraints
        for i in range(a, b + 1):
            for u in range(self.n):
                for v in range(self.n):
                    if u != v:
                        model.addConstr(
                            gp.quicksum(f[i, s, t, u, v] for (s, t, _) in self.steps[i - 1])
                            <= self.c * x[u, v]
                        )

        for i in range(a, b + 1):
            # We assume that m_i is same across all nodes,
            # even in multi-port case i.e., same size sent on all ports
            _, _, _bits =  self.steps[i - 1][0]
            model.addQConstr(theta[i] * T[i] >= self.beta * _bits)

        model.setObjective(gp.quicksum(T[i] for i in range(a, b + 1)), GRB.MINIMIZE)
        model.optimize()

        if model.Status != GRB.OPTIMAL:
            topo = {}
            # if model.Status == GRB.INFEASIBLE:
            #     print("Infeasible model. Check the constraints")
            cost = math.inf
            self._cache[key] = (topo, cost)
            return topo, cost

        topo: Topology = {}
        for (u, v), var in x.items():
            val = var.X
            if val > 0.5:
                topo[(u, v)] = int(round(val))

        cost = model.ObjVal
        self._cache[key] = (topo, cost)
        return topo, cost


    def synthesize_for_k(self, k: int) -> Tuple[float, List[Tuple[Topology, int]]]:
        DP = [[math.inf] * (k + 1) for _ in range(self.s + 2)]
        nxt = [[None] * (k + 1) for _ in range(self.s + 2)]
        topo = [[None] * (k + 1) for _ in range(self.s + 2)]

        for a in range(1, self.s + 2):
            b = self.s + 1
            G, cost = self.completion_time(a, b-1)
            # print ("a,b,t",a,b,0,k)
            DP[a][0] = cost
            nxt[a][0] = b
            topo[a][0] = G
            # print(G)

        DP[self.s + 1][k] = 0.0

        for t in range(1, k + 1):
            for a in range(1, self.s + 1):
                best = math.inf
                best_b = None
                best_G = None
                for b in range(a + 1, self.s + 2):
                    # print ("a,b,t",a,b,t)
                    # Note: for completion_time(x,y), we always assume steps x until y, *including* y.
                    G, v1 = self.completion_time(a, b - 1)
                    # if (k==3 and a==3):
                    #     print(v1,DP[b][t - 1],b,t)
                    v = v1 + DP[b][t - 1]
                    if v < best:
                        best = v
                        best_b = b
                        best_G = G
                DP[a][t] = best
                nxt[a][t] = best_b
                topo[a][t] = best_G

        schedule: List[Tuple[Topology, int]] = []
        a = 1
        t = k
        # print("t=",k)
        while t >= 0:
            # if (k==3):
            #     print(a,b,k,t)
            b = nxt[a][t]
            if b is None:
                break
            if b <= self.s+1:
                # if (k==3):
                #     print(topo[a][t])
                schedule.append((topo[a][t], b))
            a = b
            t -= 1

        return DP[1][k], schedule

    def synthesize(self) -> Tuple[float, List[Tuple[Topology, int]]]:
        best_cost = math.inf
        best_schedule: List[Tuple[Topology, int]] = []
        for k in range(0, self.s + 1):
            cost_no_reconf, sched = self.synthesize_for_k(k)
            # print(k,sched)
            total_cost = cost_no_reconf + k * self.alpha_r
            # print("k=",k,"cost=",total_cost)
            if total_cost < best_cost:
                best_cost = total_cost
                best_schedule = sched
        return best_cost, best_schedule

    def expandSchedulePerStep(self,
        schedule: List[Tuple[Topology, int]],
        num_steps: int,
    ) -> List[Topology]:
        per_step = [None] * num_steps

        cur_step = 1
        for topo, b in schedule:
            end = b - 1
            for s in range(cur_step, end + 1):
                per_step[s - 1] = topo
            cur_step = b

        # If last segment goes until the end
        if cur_step <= num_steps:
            last_topo = schedule[-1][0] if schedule else {}
            for s in range(cur_step, num_steps + 1):
                per_step[s - 1] = last_topo

        return per_step