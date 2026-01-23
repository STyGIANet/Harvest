#include "DPSchedulerPath.h"

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

static constexpr int K_PATHS = 8;
static constexpr int MAX_PATH_LEN = 64; // It is a bit extreme but fine for now..

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
  const std::vector<uint64_t>& chunksizes,
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
  if (A.size() != B.size()) return false;
  for (const auto& kv : A) {
    auto it = B.find(kv.first);
    if (it == B.end()) return false;
    if (it->second != kv.second) return false;
  }
  return true;
}

std::vector<int> DPScheduler::bfs_parent(
  const std::vector<std::vector<int>>& adj,
  int s,
  int t,
  const std::unordered_set<Edge, EdgeHash>* bannedEdges,
  const std::unordered_set<int>* bannedNodes
) const {
  std::vector<int> parent((size_t)n_, -1);
  std::deque<int> q;

  if (bannedNodes && bannedNodes->count(s)) return parent;
  if (bannedNodes && bannedNodes->count(t)) return parent;

  parent[(size_t)s] = s;
  q.push_back(s);

  while (!q.empty()) {
    int u = q.front();
    q.pop_front();
    if (u == t) break;

    for (int v : adj[(size_t)u]) {
      if (bannedNodes && bannedNodes->count(v)) continue;
      if (bannedEdges && bannedEdges->count(Edge{u,v})) continue;
      if (parent[(size_t)v] != -1) continue;

      parent[(size_t)v] = u;
      q.push_back(v);
    }
  }
  return parent;
}

bool DPScheduler::reconstruct_path_edges(int s, int t, const std::vector<int>& parent, Path& out) const {
  out.clear();
  if (parent[(size_t)t] == -1) return false;
  if (parent[(size_t)s] == -1) return false;

  int cur = t;
  std::vector<int> nodes;
  nodes.reserve((size_t)n_);
  while (cur != s) {
    int p = parent[(size_t)cur];
    if (p == -1) return false;
    if (p == cur) break;
    nodes.push_back(cur);
    cur = p;
  }
  nodes.push_back(s);
  std::reverse(nodes.begin(), nodes.end());
  if (nodes.size() < 2) return false;

  out.reserve(nodes.size() - 1);
  for (size_t i = 0; i + 1 < nodes.size(); ++i) {
    out.push_back(Edge{nodes[i], nodes[i+1]});
  }
  return true;
}

std::vector<Path> DPScheduler::k_shortest_paths_yen(
  const std::vector<std::vector<int>>& adj,
  int s, int t,
  int K,
  int maxPathLen
) const {
  std::vector<Path> A;
  A.reserve((size_t)K);

  {
    Path p0;
    auto parent = bfs_parent(adj, s, t, nullptr, nullptr);
    if (!reconstruct_path_edges(s, t, parent, p0)) return A;
    if ((int)p0.size() > maxPathLen) return A;
    A.push_back(std::move(p0));
  }

  struct Cand {
    Path path;
    int  cost;
  };
  std::vector<Cand> B;
  B.reserve((size_t)K * 8);

  auto path_cost = [](const Path& p) { return (int)p.size(); };

  for (int k = 1; k < K; ++k) {
    const Path& prev = A[(size_t)k - 1];

    std::vector<int> prevNodes;
    prevNodes.reserve(prev.size() + 1);
    prevNodes.push_back(prev.front().u);
    for (const auto& e : prev) prevNodes.push_back(e.v);

    for (int i = 0; i < (int)prevNodes.size() - 1; ++i) {
      int spurNode = prevNodes[(size_t)i];

      Path rootPath;
      rootPath.reserve((size_t)i);
      for (int j = 0; j < i; ++j) rootPath.push_back(prev[(size_t)j]);

      std::unordered_set<Edge, EdgeHash> bannedEdges;
      bannedEdges.reserve(64);

      for (const auto& p : A) {
        if ((int)p.size() < i) continue;

        bool sameRoot = true;
        for (int j = 0; j < i; ++j) {
          if (!(p[(size_t)j] == rootPath[(size_t)j])) { sameRoot = false; break; }
        }
        if (sameRoot) {
          bannedEdges.insert(p[(size_t)i]);
        }
      }

      std::unordered_set<int> bannedNodes;
      bannedNodes.reserve(64);
      for (int j = 0; j < i; ++j) {
        bannedNodes.insert(prevNodes[(size_t)j]);
      }
      bannedNodes.erase(spurNode);

      auto parent = bfs_parent(adj, spurNode, t, &bannedEdges, &bannedNodes);
      Path spurPath;
      if (!reconstruct_path_edges(spurNode, t, parent, spurPath)) {
        continue;
      }

      Path total = rootPath;
      total.insert(total.end(), spurPath.begin(), spurPath.end());

      int cost = path_cost(total);
      if (cost > maxPathLen) continue;
      bool dup = false;
      for (const auto& c : B) {
        if (c.cost != cost) continue;
        if (c.path.size() != total.size()) continue;
        bool eq = true;
        for (size_t z = 0; z < total.size(); ++z) {
          if (!(c.path[z] == total[z])) { eq = false; break; }
        }
        if (eq) { dup = true; break; }
      }
      if (!dup) B.push_back(Cand{std::move(total), cost});
    }

    if (B.empty()) break;

    auto bestIt = std::min_element(B.begin(), B.end(), [](const Cand& a, const Cand& b){
      if (a.cost != b.cost) return a.cost < b.cost;
      size_t L = std::min(a.path.size(), b.path.size());
      for (size_t i = 0; i < L; ++i) {
        if (a.path[i].u != b.path[i].u) return a.path[i].u < b.path[i].u;
        if (a.path[i].v != b.path[i].v) return a.path[i].v < b.path[i].v;
      }
      return a.path.size() < b.path.size();
    });

    A.push_back(std::move(bestIt->path));
    B.erase(bestIt);
  }

  return A;
}

std::pair<Topology, double> DPScheduler::completion_time(int a, int b) {
  std::pair<int,int> key{a,b};
  auto itc = cache_.find(key);
  if (itc != cache_.end()) return itc->second;

  if (logging_ == 1) {
    std::cout << "\n\n\n\n##### Solving for steps a=" << a << ", b=" << b << " #####\n";
  }

  std::vector<Topology> y;
  y.reserve((size_t)(n_ + s_ + 10));
  int topoSpace = 0;

  Topology base = base_topology();

  for (int shift = 0; shift < n_ - 1; ++shift) {
    if (rd_ == 1 && shift >= 1) break;

    Topology topo;
    topo.reserve((size_t)n_ * (size_t)(n_ - 1));
    for (int u = 0; u < n_; ++u) {
      for (int v = 0; v < n_; ++v) {
        if (u == v) continue;
        topo[Edge{u,v}] = 0;
      }
    }
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
    for (const auto& dmd : steps_[(size_t)i - 1]) {
      int s = dmd.s;
      int t = dmd.t;
      uint64_t demand = dmd.bits;
      // std::cout << "demand " << demand << " chunksizes " << chunksizes_[(size_t)i - 1] << "\n";
      uint64_t k = (uint64_t)(demand / chunksizes_[(size_t)i - 1]);
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

  // Lets leave this out as a way to see progress
  std::cout << "\n\n\n\n##### Solving for steps a=" << a << ", b=" << b << " #####\n";
  if (logging_){
    std::cout << "total = " << topoSpace << "\n";
  }

  std::vector<double> objectiveValue((size_t)topoSpace, INF_D);

  for (int search = 0; search < topoSpace; ++search) {
    const Topology& x = y[(size_t)search];

    auto t0 = std::chrono::steady_clock::now();

    std::vector<Edge> edges;
    edges.reserve(x.size());
    for (const auto& kv : x) {
      const Edge& e = kv.first;
      int cap = kv.second;
      if (cap > 0 && e.u != e.v) edges.push_back(e);
    }

    std::vector<std::vector<int>> adj((size_t)n_);
    for (const auto& e : edges) {
      adj[(size_t)e.u].push_back(e.v);
    }

    std::unordered_set<Pair, PairHash> stSet;
    stSet.reserve(256);
    for (int i = a; i <= b; ++i) {
      for (const auto& dmd : steps_[(size_t)i - 1]) {
        stSet.insert({dmd.s, dmd.t});
      }
    }

    std::unordered_map<int, std::unordered_set<int>> bySource;
    bySource.reserve(64);
    for (const auto& st : stSet) {
      bySource[st.first].insert(st.second);
    }
    if (!checkReachable(adj, bySource)) {
      continue;
    }

    std::unordered_map<Pair, std::vector<Path>, PairHash> P;
    P.reserve(stSet.size());

    bool ok = true;
    for (const auto& st : stSet) {
      int s = st.first;
      int t = st.second;
      auto paths = k_shortest_paths_yen(adj, s, t, K_PATHS, MAX_PATH_LEN);
      if (paths.empty()) { ok = false; break; }
      P.emplace(st, std::move(paths));
    }
    if (!ok) {
      std::cout << "Not ok" << std::endl;
      continue;
    }

    try {
      GRBEnv env = GRBEnv(true);
      env.set(GRB_IntParam_OutputFlag, logging_);
      env.start();

      GRBModel model = GRBModel(env);

      model.set(GRB_IntParam_Threads, 1);
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
        // This is frustrating....
        // The T variable is causing numerical issues randomly 
        T[(size_t)i]     = model.addVar(0, GRB_INFINITY, 0.0, GRB_CONTINUOUS, "T_" + std::to_string(i));
      }

      std::unordered_map<PathKey, GRBVar, PathKeyHash> g;
      g.reserve( (size_t)(b-a+1) * stSet.size() * (size_t)K_PATHS );

      for (int i = a; i <= b; ++i) {
        for (const auto& dmd : steps_[(size_t)i - 1]) {
          Pair st{dmd.s, dmd.t};
          const auto& paths = P.at(st);
          for (int pidx = 0; pidx < (int)paths.size(); ++pidx) {
            PathKey k{i, dmd.s, dmd.t, pidx};
            g.emplace(k, model.addVar(0.0, (double)d_, 0.0, GRB_CONTINUOUS));
          }
        }
      }

      for (int i = a; i <= b; ++i) {
        double inv = 1.0 / (double)chunksizes_[(size_t)i - 1];
        for (const auto& dmd : steps_[(size_t)i - 1]) {
          int s = dmd.s;
          int t = dmd.t;
          int dint = (int)std::floor((double)dmd.bits * inv);

          Pair st{s,t};
          const auto& paths = P.at(st);

          GRBLinExpr sum = 0.0;
          for (int pidx = 0; pidx < (int)paths.size(); ++pidx) {
            PathKey k{i,s,t,pidx};
            auto it = g.find(k);
            if (it != g.end()) sum += it->second;
          }

          model.addConstr(sum == theta[(size_t)i] * (double)dint);
        }
      }

      for (int i = a; i <= b; ++i) {
        // edgeInc[e] contains the set of all (s,t,pidx) where path pidx for (s,t) contains edge e
        // This is same as helpful for capacity constratins where we need to sum flows on an edge
        std::unordered_map<Edge, std::vector<std::tuple<int,int,int>>, EdgeHash> edgeInc;
        edgeInc.reserve(edges.size() * 2);

        for (const auto& dmd : steps_[(size_t)i - 1]) {
          int s = dmd.s;
          int t = dmd.t;
          Pair st{s,t};
          const auto& paths = P.at(st);
          for (int pidx = 0; pidx < (int)paths.size(); ++pidx) {
            const Path& path = paths[(size_t)pidx];
            for (const auto& e : path) {
              edgeInc[e].push_back({s,t,pidx});
            }
          }
        }

        for (const auto& e : edges) {
          int cap = x.at(e);
          GRBLinExpr sum = 0.0;

          auto itInc = edgeInc.find(e);
          if (itInc != edgeInc.end()) {
            for (const auto& tup : itInc->second) {
              int s, t, pidx;
              std::tie(s,t,pidx) = tup;
              PathKey k{i,s,t,pidx};
              auto itg = g.find(k);
              if (itg != g.end()) sum += itg->second;
            }
          }

          model.addConstr(sum <= (double)cap);
        }
      }

      // Ti is basically transmission time. So lets interpret it in nanosecond, or in seconds based on our convinience
      double SCALE = 1; // Makes Ti in nanoseconds
      for (int i = a; i <= b; ++i) {
        double bits = (double)chunksizes_[(size_t)i - 1];
        if (beta_ * bits > 1e3){
          SCALE = 1e-9; // Makes Ti in seconds
        }
      }

      for (int i = a; i <= b; ++i) {
        double bits = (double)chunksizes_[(size_t)i - 1];
        // model.addQConstr(2 * theta[(size_t)i] * T[(size_t)i] == 2 * beta_ * bits);
        GRBVar th = theta[(size_t)i];
        GRBVar Ti = T[(size_t)i];

        // Ti is basically transmission time. So lets interpret it in nanosecond, or in seconds based on our convinience

        GRBQuadExpr lhs = (th - Ti) * (th - Ti) + 4.0 * beta_ * bits * SCALE;
        GRBQuadExpr rhs = (th + Ti) * (th + Ti);
        // The inequality here speeds up the optimizer, but even with exact same objective value, it flips to suboptimal status somehow.
        // Definitely looks like a numeric issue and suboptimality could perhaps just be a floating point difference
        model.addQConstr(lhs <= rhs); 
      }

      GRBLinExpr obj = 0.0;
      for (int i = a; i <= b; ++i) {
        double bits = (double)chunksizes_[(size_t)i - 1];
        // if (SCALE == 1)
        //   // Everything is nanoseconds here
        //   obj += alpha_ + T[(size_t)i] * (1.0 + (delta_ / (beta_ * bits)));
        // else{
          // Everything is converted to seconds here.
          // obj += alpha_*SCALE + T[(size_t)i] + delta_ * ( T[(size_t)i] / (beta_ * bits));
        // }
        // Since scale is 1 anyway otherwise, getting rid of if else
        // T[(size_t)i] / (beta_ * bits) this term is theta and unitless
        obj += alpha_*SCALE + T[(size_t)i] + delta_*SCALE * ( T[(size_t)i] / (beta_ * bits));
      }
      model.setObjective(obj, GRB_MINIMIZE);

      model.optimize();

      auto t1 = std::chrono::steady_clock::now();
      if (logging_){
        std::cout << "Done in " << std::chrono::duration<double>(t1 - t0).count() << " cost " << uint32_t (model.get(GRB_DoubleAttr_ObjVal)/SCALE) << std::endl;
      }

      if (logging_) {
        std::cout << "Status " << model.get(GRB_IntAttr_Status) << "\n";
        std::cout << "ObjVal " << model.get(GRB_DoubleAttr_ObjVal) << "\n";
        std::cout << "IterCount " << model.get(GRB_DoubleAttr_IterCount) << "\n";
        std::cout << "BarIterCount " << model.get(GRB_IntAttr_BarIterCount) << "\n";
      }

      int status = model.get(GRB_IntAttr_Status);
      if (status != GRB_OPTIMAL && status != GRB_SUBOPTIMAL) {
        objectiveValue[(size_t)search] = INF_D;
      } else {
        objectiveValue[(size_t)search] = model.get(GRB_DoubleAttr_ObjVal)/SCALE;
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
    std::cout << "minIndex " << minIndex << " minObj " << minObj << "\n";
    assert(false);
  }

  Topology topo = y[(size_t)minIndex];

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
    if (logging_) {
      std::cout << "###### Solving for " << k << " reconfigurations\n";
    }
    auto [cost_no_reconf, sched] = synthesize_for_k(k);
    double total_cost = cost_no_reconf + (double)k * alpha_r_;
    if (total_cost < best_cost) {
      if (std::fabs(total_cost - best_cost) < 1e-4 && best_k <= k) continue; 
      if (logging_)
        std::cout << "total cost " << total_cost << " best cost " << best_cost << " best k " << best_k << " k " << k << std::endl;
      best_cost = total_cost;
      best_schedule = std::move(sched);
      best_total_reconf_cost = (double)k * alpha_r_;
      best_k = k;
      if (logging_){
        std::cout << "k: " << k << " total_cost: " << total_cost
                << " total reconf cost: " << best_total_reconf_cost << "\n";
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
