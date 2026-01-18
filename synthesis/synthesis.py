from typing import List, Tuple, Dict
import math
import gurobipy as gp
from gurobipy import GRB
import random
import time
import os

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
        alpha: float,
        delta: float,
        alpha_r: float,
        dims: List[int],
        chunksizes: List[int],
        relaxation: int,
        logging: int,
        rd: int,
    ):
        self.steps = steps
        self.s = len(steps)
        self.n = num_nodes
        self.d = d
        self.c = c
        self.beta = beta
        self.alpha = alpha
        self.delta = delta
        self.alpha_r = alpha_r
        self.dims = dims
        self.chunksizes = chunksizes
        self.relaxation = relaxation
        self.logging = logging
        self.rd = rd
        self._cache: Dict[Tuple[int, int], Tuple[Topology, float]] = {}

        model = gp.Model()
        model.Params.OutputFlag = self.logging
        # model.Params.MIPFocus = 1
        # model.Params.Heuristics = 0.5
        # model.Params.Cuts = 1
        # model.Params.NonConvex = 2
        # model.Params.MIPGap = 0.05

        # model.Params.PoolSearchMode = 2
        # model.Params.PoolSolutions = 10
        # model.Params.PoolGap = 1e10
        model.Params.Threads = os.cpu_count()
        # model.Params.TimeLimit = 2
        # model.Params.Presolve = 2

        I = list(range(self.s+1))

        # Concurrent flow theta variable
        # Lets give an epsilon for the lb, so that the inverse doesn't go to infinity
        theta = model.addVars(I,lb=1e-6,ub=1,name="theta")
        # auxiliary variable corresponding to the transmission time
        T = model.addVars(I,lb=0,ub=20e6,name="T") # Limiting to 20 milliseconds for the transmission delay
        # flow variable for ith step, for demand s,t, traversing edge u,v
        flow_index = []
        for i in range(1,self.s+1):
            if self.logging:
                print("adding flow indices", i)
            for (s, t, _) in self.steps[i-1]:
                for u in range(self.n):
                    for v in range(self.n):
                        if u != v:
                            flow_index.append((i, s, t, u, v))

        # print(flow_index.index((15,0,15,0,1)))
        # exit()

        if self.logging:
            print("adding flow vars")
        f = model.addVars(flow_index,lb=0,ub=self.d,name="f")
        if self.logging:
            print("finished adding flow vars")


        self.model = model
        self.T = T
        self.theta = theta
        self.f = f

    def ringNext(self,u, n):
        return (u + 1) % n

    def ringPrev(self,u, n):
        return (u - 1) % n

    def torusNeighbors(self,u, dims):
        X, Y = dims
        y = u % Y
        x = u // Y

        nbrs = [
            ((x + 1) % X, y),
            ((x - 1) % X, y),
            (x, (y + 1) % Y),
            (x, (y - 1) % Y),
        ]
        return [(nx * Y + ny) for (nx, ny) in nbrs]

    def base_topology(self):
        base = {}
        for u in range(self.n):
            for v in range(self.n):
                if u == v:
                    continue

                val = 0
                if self.d == 1:
                    if v == self.ringNext(u, self.n):
                        val = 1
                elif self.d == 2:
                    if v == self.ringNext(u, self.n) or v == self.ringPrev(u, self.n):
                        val = 1
                elif self.d == 4:
                    if v in self.torusNeighbors(u, self.dims):
                        val = 1

                if val:
                    base[(u, v)] = 1
                else:
                    base[(u, v)] = 0
        return base

    def completion_time(self, a: int, b: int) -> Tuple[Topology, float]:
        key = (a, b)

        ts = time.perf_counter_ns()
        if key in self._cache:
            return self._cache[key]
        else:
            if self.logging==1:
                print(f'\n\n\n\n##### Solving for steps a={a}, b={b} #####')


        x = {}
        z = {}
        y = {}
        topoSpace = 0


        # A base topology as a safe fallback that is capable of serving any step
        base = self.base_topology()
        for shift in range(self.n-1):
            if shift!=0 and math.gcd(shift, self.n) != 1:
                continue
            if self.rd == 1 and shift>=1:
                break
            y[topoSpace] = {}
            for u in range(self.n):
                for v in range(self.n):
                    if u==v:
                        continue
                    y[topoSpace][u,v]=0
            for (u, v), val in base.items():
                uprime = (u) % self.n
                vprime = (v + shift) % self.n
                if uprime==vprime:
                    continue
                y[topoSpace][uprime, vprime] = val
            topoSpace += 1

        # Collection of topologies to choose from
        if self.rd == 1:
            start = a
            end = a+1
        else:
            start = 1
            end = self.s+1

        for i in range(start,end):
        # for i in range(1,a+1):
            if i>len(self.steps):
                continue
            # direct connect topo corresponding to step i
            y[topoSpace] = {}
            temp = {}
            for u in range(self.n):
                for v in range(self.n):
                    if u==v:
                        continue
                    temp[u,v]=0
            for (s, t, demand) in self.steps[i - 1]:
                # interpreted as the ideal number of links for direct transmission
                temp[s,t]=int(demand/self.chunksizes[i-1])
            redundant = False
            for keyprime in y.keys():
                if temp == y[keyprime]:
                    redundant = True
                    # print("redundant")
                    break
            if redundant==False:
                y[topoSpace] = temp
                # print("New")
                # print(y[topoSpace])
                # print()
                topoSpace = topoSpace + 1

        if self.logging == 1:
            # print(f'\n\n\n\n##### Solving for steps a={a}, b={b} #####')
            print("total = ", topoSpace)

        # ToDo: Could add other relevant topos to the topoSpace

        # for i in range(self.n):
        #     for u in range(self.n):
        #         for d in range(self.n):
        #             y[i][u,(u+d)%n] = 1

        model = self.model
        T = self.T
        theta = self.theta
        f = self.f

        objectiveValue = list()
        for search in range(topoSpace):
            tsprime = time.perf_counter_ns()
            model.remove(model.getConstrs())
            model.update()
            
            x = y[search]

            # Flow conservation and demand constraints
            for i in range(a, b + 1): # For each step between a, b (including)
                for (s, t, demand) in self.steps[i - 1]: # Note: Algorithm's steps are indexed from 1
                    for u in range(self.n):
                        outflow = gp.quicksum(f[i, s, t, u, v] for v in range(self.n) if u != v)
                        inflow = gp.quicksum(f[i, s, t, v, u] for v in range(self.n) if u != v)
                        if u == s:
                            model.addConstr(outflow - inflow == theta[i]*int(demand/self.chunksizes[i-1]))
                        elif u == t:
                            model.addConstr(outflow - inflow == -theta[i]*int(demand/self.chunksizes[i-1]))
                        else:
                            model.addConstr(outflow - inflow == 0)

            # Capacity constraints
            for i in range(a, b + 1):
                for u in range(self.n):
                    for v in range(self.n):
                        if u != v:
                            model.addConstr(
                                gp.quicksum(f[i, s, t, u, v] for (s, t, _) in self.steps[i - 1])
                                <= x[u, v]
                            )

            for i in range(a, b + 1):
                # We assume that m_i is same across all nodes within a single step,
                # even in multi-port case i.e., same size sent on all ports
                _bits = self.chunksizes[i-1]
                # model.addQConstr(theta[i] * T[i] == self.beta * _bits)
                # converting to soc constraint, see appendix
                model.addQConstr((theta[i] - T[i]) * (theta[i] - T[i])+ 4.0 * self.beta * _bits<= (theta[i] + T[i]) * (theta[i] + T[i]))

            if self.relaxation == 1:
                model.setObjective(gp.quicksum(self.alpha+T[i]*(1+ self.delta/(self.beta * self.chunksizes[i-1])) for i in range(a, b + 1)), GRB.MINIMIZE)
            else:
                model.setObjective(gp.quicksum(self.alpha+T[i]*(1+ self.delta/(self.beta * self.chunksizes[i-1])) for i in range(a, b + 1)), GRB.MINIMIZE)
            model.optimize()
            if model.Status != GRB.OPTIMAL:
                cost = math.inf
                objectiveValue.append(cost)
            else:
                objectiveValue.append(model.ObjVal)
            
            if self.logging:
                print("instanceTime =",(time.perf_counter_ns()-tsprime)/1e9)

        minIndex, minObj = min(enumerate(objectiveValue), key=lambda lam: lam[1])
        # print(minIndex, minObj)
        topo: Topology = y[minIndex]
        topo = {k: v for k, v in topo.items() if v != 0}
        cost = minObj
        if topo=={}:
            print("###################")
            assert(False)

        self._cache[key] = (topo, cost)
        if self.logging:
            print("time=",(time.perf_counter_ns()-ts)/1e9)
        return topo, cost


    def synthesize_for_k(self, k: int) -> Tuple[float, List[Tuple[Topology, int]]]:
        DP = [[math.inf] * (k + 1) for _ in range(self.s + 2)]
        nxt = [[None] * (k + 1) for _ in range(self.s + 2)]
        topo = [[None] * (k + 1) for _ in range(self.s + 2)]

        for a in range(1, self.s + 1):
            b = self.s + 1
            G, cost = self.completion_time(a, b-1)
            # print ("a,b,t",a,b,0,k)
            DP[a][0] = cost
            nxt[a][0] = b
            topo[a][0] = G
            # print(G)

        DP[self.s + 1][k] = 0.0

        for t in range(1, k + 1):
            # print(f"solving for t={t}")
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
            if self.logging:
                print(f"###### Solving for {k} reconfigurations")
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
        print((schedule))
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