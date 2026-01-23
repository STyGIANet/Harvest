#include "DPScheduler.h"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <deque>
#include <limits>
#include <iostream>
#include <thread>
#include <chrono>
#include <cstdint>


static constexpr double INF_D = std::numeric_limits<double>::infinity();

DPScheduler::DPScheduler(
  const std::vector<std::vector<Demand>>& steps,
  int num_nodes,
  int d,
  double c,
  double beta,
  double alpha,
  double delta,
  double alpha_r,
  const std::vector<int>& dims,
  const std::vector<int>& chunksizes,
  int relaxation,
  int logging,
  int rd
)
: steps_(steps),
  s_((int)steps.size()),
  n_(num_nodes),
  d_(d),
  c_(c),
  beta_(beta),
  alpha_(alpha),
  delta_(delta),
  alpha_r_(alpha_r),
  dims_(dims),
  chunksizes_(chunksizes),
  relaxation_(relaxation),
  logging_(logging),
  rd_(rd) {}

int DPScheduler::ringNext(int u) const { return (u + 1) % n_; }
int DPScheduler::ringPrev(int u) const { return (u - 1 + n_) % n_; }

std::vector<int> DPScheduler::torusNeighbors(int u) const {
  // dims_ is [X,Y]
  int X = dims_.at(0);
  int Y = dims_.at(1);
  int y = u % Y;
  int x = u / Y;

  auto idx = [&](int xx, int yy) { return xx * Y + yy; };

  std::vector<int> nbrs;
  nbrs.push_back(idx((x + 1) % X, y));
  nbrs.push_back(idx((x - 1 + X) % X, y));
  nbrs.push_back(idx(x, (y + 1) % Y));
  nbrs.push_back(idx(x, (y - 1 + Y) % Y));
  return nbrs;
}

Topology DPScheduler::base_topology() const {
  Topology base;
  base.reserve((size_t)n_ * (size_t)(n_ - 1));

  for (int u = 0; u < n_; ++u) {
    for (int v = 0; v < n_; ++v) {
      if (u == v) continue;

      int val = 0;
      if (d_ == 1) {
        if (v == ringNext(u)) val = 1;
      } else if (d_ == 2) {
        if (v == ringNext(u) || v == ringPrev(u)) val = 1;
      } else if (d_ == 4) {
        auto nbrs = torusNeighbors(u);
        if (std::find(nbrs.begin(), nbrs.end(), v) != nbrs.end()) val = 1;
      }
      base[Edge{u,v}] = val;
    }
  }
  return base;
}

bool DPScheduler::checkReachable(
  const std::vector<std::vector<int>>& adj,
  const std::unordered_map<int, std::unordered_set<int>>& bySource
) const {
  std::vector<char> visited((size_t)n_, 0);
  std::deque<int> q;

  for (const auto& kv : bySource) {
    int s = kv.first;
    const auto& targets = kv.second;

    std::fill(visited.begin(), visited.end(), 0);
    q.clear();

    visited[(size_t)s] = 1;
    q.push_back(s);

    while (!q.empty()) {
      int u = q.front();
      q.pop_front();
      for (int v : adj[(size_t)u]) {
        if (!visited[(size_t)v]) {
          visited[(size_t)v] = 1;
          q.push_back(v);
        }
      }
    }

    for (int t : targets) {
      if (!visited[(size_t)t]) return false;
    }
  }

  return true;
}

static bool topoEqualFull(const Topology& A, const Topology& B) {
  // Both are expected to have all (u,v) pairs (u!=v) with 0/1/... values.
  // We can compare size then exact key/value equality.
  if (A.size() != B.size()) return false;
  for (const auto& kv : A) {
    auto it = B.find(kv.first);
    if (it == B.end()) return false;
    if (it->second != kv.second) return false;
  }
  return true;
}

std::pair<Topology, double> DPScheduler::completion_time(int a, int b) {
  std::pair<int,int> key{a,b};
  auto itc = cache_.find(key);
  if (itc != cache_.end()) return itc->second;

  if (logging_ == 1) {
    std::cout << "\n\n\n\n##### Solving for steps a=" << a << ", b=" << b << " #####\n";
  }

  // Build topology search space y
  std::vector<Topology> y;
  y.reserve((size_t)(n_ + s_ + 10));
  int topoSpace = 0;

  // base topology full map (includes zeros)
  Topology base = base_topology();

  // shifts (0..n-2)
  for (int shift = 0; shift < n_ - 1; ++shift) {
    if (rd_ == 1 && shift >= 1) break;

    Topology topo;
    topo.reserve((size_t)n_ * (size_t)(n_ - 1));
    // init all to zero
    for (int u = 0; u < n_; ++u) {
      for (int v = 0; v < n_; ++v) {
        if (u == v) continue;
        topo[Edge{u,v}] = 0;
      }
    }
    // shift v by 'shift'
    for (const auto& kv : base) {
      const Edge& e = kv.first;
      int val = kv.second;
      int uprime = e.u % n_;
      int vprime = (e.v + shift) % n_;
      if (uprime == vprime) continue;
      topo[Edge{uprime, vprime}] = val;
    }
    y.push_back(std::move(topo));
    topoSpace++;
  }

  int start = (rd_ == 1 ? a : 1);
  int end   = (rd_ == 1 ? a + 1 : s_ + 1);

  for (int i = start; i < end; ++i) {
    if (i > (int)steps_.size()) continue;

    Topology temp;
    temp.reserve((size_t)n_ * (size_t)(n_ - 1));

    for (int u = 0; u < n_; ++u) {
      for (int v = 0; v < n_; ++v) {
        if (u == v) continue;
        temp[Edge{u,v}] = 0;
      }
    }

    // direct connect based on step i
    for (const auto& dmd : steps_[(size_t)i - 1]) {
      int s = dmd.s;
      int t = dmd.t;
      int demand = dmd.bits;
      int k = (int)(demand / chunksizes_[(size_t)i - 1]);
      temp[Edge{s,t}] = k;
    }

    bool redundant = false;
    for (const auto& prev : y) {
      if (topoEqualFull(temp, prev)) {
        redundant = true;
        break;
      }
    }
    if (!redundant) {
      y.push_back(std::move(temp));
      topoSpace++;
    }
  }

  // if (logging_){
    std::cout << "\n\n\n\n##### Solving for steps a=" << a << ", b=" << b << " #####\n";
    std::cout << "total = " << topoSpace << "\n";
  // }

  std::vector<double> objectiveValue((size_t)topoSpace, INF_D);

  // For each topology candidate
  for (int search = 0; search < topoSpace; ++search) {
    const Topology& x = y[(size_t)search];

    auto t0 = std::chrono::steady_clock::now();

    // Build edges list only for x with >0 capacity
    std::vector<Edge> edges;
    edges.reserve(x.size());
    for (const auto& kv : x) {
      const Edge& e = kv.first;
      int cap = kv.second;
      if (cap > 0 && e.u != e.v) edges.push_back(e);
    }

    // reachability check
    std::vector<std::vector<int>> adj((size_t)n_);
    adj.reserve((size_t)n_);
    for (const auto& e : edges) {
      adj[(size_t)e.u].push_back(e.v);
    }

    std::unordered_set<std::pair<int,int>, PairHash> demands;
    for (int i = a; i <= b; ++i) {
      for (const auto& dmd : steps_[(size_t)i - 1]) {
        demands.insert({dmd.s, dmd.t});
      }
    }
    std::unordered_map<int, std::unordered_set<int>> bySource;
    for (const auto& st : demands) {
      bySource[st.first].insert(st.second);
    }

    if (!checkReachable(adj, bySource)) {
      // No need to solve, we know it will be an infeasible solution
      continue;
    }

    // in and out neighbours, helpful for flow conservation constraints
    std::vector<std::vector<int>> outN((size_t)n_), inN((size_t)n_);
    std::vector<char> activeFlag((size_t)n_, 0);
    for (const auto& e : edges) {
      outN[(size_t)e.u].push_back(e.v);
      inN[(size_t)e.v].push_back(e.u);
    }
    std::vector<int> active;
    active.reserve((size_t)n_);
    for (int u = 0; u < n_; ++u) {
      if (!outN[(size_t)u].empty() || !inN[(size_t)u].empty()) {
        activeFlag[(size_t)u] = 1;
        active.push_back(u);
      }
    }

    try {
      GRBEnv env = GRBEnv(true);
      env.set(GRB_IntParam_OutputFlag, logging_);
      env.start();

      GRBModel model = GRBModel(env);

      model.set(GRB_IntParam_OutputFlag, logging_);
      // model.set(GRB_IntParam_Threads, (int)std::max(1u, std::thread::hardware_concurrency()));
      model.set(GRB_IntParam_Threads, 2);
      model.set(GRB_IntParam_Method, 2);
      model.set(GRB_IntParam_Presolve, 2);
      model.set(GRB_IntParam_BarHomogeneous, 0);
      model.set(GRB_DoubleParam_BarConvTol, 1e-6);
      model.set(GRB_IntParam_NumericFocus, 0);
      model.set(GRB_IntParam_Crossover, 0);


      int Imax = s_;
      std::vector<GRBVar> theta((size_t)Imax + 1);
      std::vector<GRBVar> T((size_t)Imax + 1);

      for (int i = 0; i <= Imax; ++i) {
        theta[(size_t)i] = model.addVar(0.01, 1.0, 0.0, GRB_CONTINUOUS, "theta_" + std::to_string(i));
        T[(size_t)i]     = model.addVar(0.01, 2, 0.0, GRB_CONTINUOUS, "T_" + std::to_string(i));
      }

      // Build flow vars only for (i,s,t,u,v) where edge exists
      std::unordered_map<FlowKey, GRBVar, FlowKeyHash> f;
      f.reserve((size_t)edges.size() * 16);

      for (int i = a; i <= b; ++i) {
        for (const auto& dmd : steps_[(size_t)i - 1]) {
          int s = dmd.s;
          int t = dmd.t;
          for (const auto& e : edges) {
            FlowKey k{i,s,t,e.u,e.v};
            f.emplace(k, model.addVar(0.0, (double)d_, 0.0, GRB_CONTINUOUS));
          }
        }
      }

      auto tf1 = std::chrono::steady_clock::now();
      // Flow conservation constraints
      for (int i = a; i <= b; ++i) {
        double inv = 1.0 / (double)chunksizes_[(size_t)i - 1];
        for (const auto& dmd : steps_[(size_t)i - 1]) {
          int s = dmd.s;
          int t = dmd.t;
          int dint = (int)std::floor((double)dmd.bits * inv);

          // nodes = active U {s,t}
          std::vector<int> nodes;
          nodes.reserve(active.size() + 2);
          nodes.insert(nodes.end(), active.begin(), active.end());
          if (!activeFlag[(size_t)s]) nodes.push_back(s);
          if (!activeFlag[(size_t)t] && t != s) nodes.push_back(t);

          for (int u : nodes) {
            GRBLinExpr out = 0.0;
            GRBLinExpr in = 0.0;

            for (int v : outN[(size_t)u]) {
              FlowKey k{i,s,t,u,v};
              auto itf = f.find(k);
              if (itf != f.end()) out += itf->second;
            }
            for (int v : inN[(size_t)u]) {
              FlowKey k{i,s,t,v,u};
              auto itf = f.find(k);
              if (itf != f.end()) in += itf->second;
            }

            GRBLinExpr rhs = 0.0;
            if (u == s)
              continue;
              // rhs = theta[(size_t)i] * (double)dint;
            else if (u == t) 
              rhs = -theta[(size_t)i] * (double)dint;

            model.addConstr(out - in <= rhs);
          }
        }
      }
      if (logging_){
        std::cout << "Flow constraints done in " << std::chrono::duration<double>(std::chrono::steady_clock::now() - tf1).count() << " seconds\n";
      }

      // Capacity constraints
      for (int i = a; i <= b; ++i) {
        for (const auto& e : edges) {
          int cap = x.at(e);
          GRBLinExpr sum = 0.0;
          for (const auto& dmd : steps_[(size_t)i - 1]) {
            FlowKey k{i, dmd.s, dmd.t, e.u, e.v};
            auto itf = f.find(k);
            if (itf != f.end()) sum += itf->second;
          }
          model.addConstr(sum <= (double)cap);
        }
      }

      const double SCALE = 1e9;

      for (int i = a; i <= b; ++i) {
        double bits = (double)chunksizes_[(size_t)i - 1];
        GRBVar th = theta[(size_t)i];
        GRBVar Ti = T[(size_t)i];

        GRBQuadExpr lhs = (th - Ti * SCALE) * (th - Ti * SCALE) + 4.0 * beta_ * bits;
        GRBQuadExpr rhs = (th + Ti * SCALE) * (th + Ti * SCALE);
        // GRBQuadExpr lhs = (th * Ti * SCALE);
        // GRBQuadExpr rhs = beta_ * bits;
        model.addQConstr(lhs <= rhs);
      }

      GRBLinExpr obj = 0.0;
      for (int i = a; i <= b; ++i) {
        double bits = (double)chunksizes_[(size_t)i - 1];
        obj += alpha_ + T[(size_t)i] * SCALE * (1.0 + delta_ / (beta_ * bits));
      }
      model.setObjective(obj, GRB_MINIMIZE);

      auto ts1 = std::chrono::steady_clock::now();
      model.optimize();
      if (logging_){
        std::cout << "Solved in " << std::chrono::duration<double>(std::chrono::steady_clock::now() - ts1).count() << " seconds\n";
      }
      auto t1 = std::chrono::steady_clock::now();
      if (logging_){
        std::cout << "Done in " << std::chrono::duration<double>(t1 - t0).count() << " cost " << model.get(GRB_DoubleAttr_ObjVal) << std::endl;
        std::cout << "Status " << model.get(GRB_IntAttr_Status) << "\n";
        std::cout << "ObjVal " << model.get(GRB_DoubleAttr_ObjVal) << "\n";
        std::cout << "IterCount " << model.get(GRB_DoubleAttr_IterCount) << "\n";
        std::cout << "BarIterCount " << model.get(GRB_IntAttr_BarIterCount) << "\n";
      }

      int status = model.get(GRB_IntAttr_Status);
      if (status != GRB_OPTIMAL) {
        objectiveValue[(size_t)search] = INF_D;
      } else {
        objectiveValue[(size_t)search] = model.get(GRB_DoubleAttr_ObjVal);
      }

    } catch (GRBException& e) {
      if (logging_) {
        std::cerr << "Gurobi exception: " << e.getMessage() << "\n";
      }
      objectiveValue[(size_t)search] = INF_D;
    } catch (...) {
      if (logging_) {
        std::cerr << "Unknown exception in completion_time\n";
      }
      objectiveValue[(size_t)search] = INF_D;
    }
  }

  // Pick best topology
  int minIndex = -1;
  double minObj = INF_D;
  for (int i = 0; i < topoSpace; ++i) {
    if (objectiveValue[(size_t)i] < minObj) {
      minObj = objectiveValue[(size_t)i];
      minIndex = i;
    }
  }

  if (minIndex < 0 || !std::isfinite(minObj)) {
    std::cerr << "###################\nNo feasible topology found for (a,b)=(" << a << "," << b << ")\n";
    std::cout << "minIndex " << minIndex << " minObj << " << minObj << "\n";

    assert(false);
  }

  Topology topo = y[(size_t)minIndex];

  // Just filter out zero values to remove non-existent edges
  Topology topoNonZero;
  topoNonZero.reserve(topo.size());
  for (const auto& kv : topo) {
    if (kv.second != 0) topoNonZero.emplace(kv.first, kv.second);
  }

  cache_[key] = {topoNonZero, minObj};
  return {topoNonZero, minObj};
}

std::pair<double, std::vector<std::pair<Topology,int>>> DPScheduler::synthesize_for_k(int k) {
  std::vector<std::vector<double>> DP((size_t)s_ + 2, std::vector<double>((size_t)k + 1, INF_D));
  std::vector<std::vector<int>> nxt((size_t)s_ + 2, std::vector<int>((size_t)k + 1, -1));
  std::vector<std::vector<Topology>> topo((size_t)s_ + 2, std::vector<Topology>((size_t)k + 1));

  for (int a = 1; a <= s_; ++a) {
    int b = s_ + 1;
    auto [G, cost] = completion_time(a, b - 1);
    DP[(size_t)a][0] = cost;
    nxt[(size_t)a][0] = b;
    topo[(size_t)a][0] = std::move(G);
  }

  DP[(size_t)s_ + 1][(size_t)k] = 0.0;

  for (int t = 1; t <= k; ++t) {
    for (int a = 1; a <= s_; ++a) {
      double best = INF_D;
      int best_b = -1;
      Topology best_G;

      for (int b = a + 1; b <= s_ + 1; ++b) {
        auto [G, v1] = completion_time(a, b - 1);
        double v = v1 + DP[(size_t)b][(size_t)t - 1];
        if (v < best) {
          best = v;
          best_b = b;
          best_G = std::move(G);
        }
      }

      DP[(size_t)a][(size_t)t] = best;
      nxt[(size_t)a][(size_t)t] = best_b;
      topo[(size_t)a][(size_t)t] = std::move(best_G);
    }
  }

  std::vector<std::pair<Topology,int>> schedule;
  int a = 1;
  int t = k;

  while (t >= 0) {
    int b = nxt[(size_t)a][(size_t)t];
    if (b < 0) break;
    if (b <= s_ + 1) {
      schedule.push_back({topo[(size_t)a][(size_t)t], b});
    }
    a = b;
    t -= 1;
    if (a > s_ + 1) break;
  }

  return {DP[1][k], schedule};
}

SchedulerResult DPScheduler::synthesize() {
  double best_cost = INF_D;
  std::vector<std::pair<Topology,int>> best_schedule;
  double best_total_reconf_cost = INF_D;
  int best_k = 0;


  for (int k = 0; k <= s_; ++k) {
    if (logging_){
      std::cout << "###### Solving for " << k << " reconfigurations\n";
    }
    auto [cost_no_reconf, sched] = synthesize_for_k(k);
    double total_cost = cost_no_reconf + (double)k * alpha_r_;
    if (total_cost < best_cost) {
      best_cost = total_cost;
      best_schedule = std::move(sched);
      best_total_reconf_cost = (double)k * alpha_r_;
      best_k = k;
      if (logging_){
        std::cout <<  "k: " << k << " total_cost without reconfig: " 
          << total_cost << "total reconf cost: "<< best_total_reconf_cost;
      }
    }
  }

  return {best_cost, best_schedule, best_total_reconf_cost, best_k};
}

std::vector<Topology> DPScheduler::expandSchedulePerStep(
  const std::vector<std::pair<Topology,int>>& schedule,
  int num_steps
) const {
  std::vector<Topology> per_step((size_t)num_steps);

  int cur_step = 1;
  for (const auto& seg : schedule) {
    const Topology& topo = seg.first;
    int b = seg.second;

    int end = b - 1;
    for (int s = cur_step; s <= end; ++s) {
      per_step[(size_t)s - 1] = topo;
    }
    cur_step = b;
  }

  if (cur_step <= num_steps) {
    Topology last_topo;
    if (!schedule.empty()) last_topo = schedule.back().first;
    for (int s = cur_step; s <= num_steps; ++s) {
      per_step[(size_t)s - 1] = last_topo;
    }
  }

  return per_step;
}
