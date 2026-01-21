#pragma once

#include <gurobi_c++.h>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <tuple>
#include <utility>

struct Demand {
  int s;
  int t;
  int bits;
};

struct Edge {
  int u;
  int v;
  bool operator==(const Edge& o) const noexcept { return u == o.u && v == o.v; }
};

struct EdgeHash {
  size_t operator()(const Edge& e) const noexcept {
    return (static_cast<size_t>(e.u) << 32) ^ static_cast<size_t>(e.v);
  }
};

using Topology = std::unordered_map<Edge, int, EdgeHash>;

struct PairHash {
  size_t operator()(const std::pair<int,int>& p) const noexcept {
    return (static_cast<size_t>(p.first) << 32) ^ static_cast<size_t>(p.second);
  }
};

struct FlowKey {
  int i, s, t, u, v;
  bool operator==(const FlowKey& o) const noexcept {
    return i==o.i && s==o.s && t==o.t && u==o.u && v==o.v;
  }
};

struct FlowKeyHash {
  size_t operator()(const FlowKey& k) const noexcept {
    // pack into hash
    size_t h = 1469598103934665603ULL;
    auto mix = [&](size_t x) {
      h ^= x + 0x9e3779b97f4a7c15ULL + (h<<6) + (h>>2);
    };
    mix((size_t)k.i);
    mix((size_t)k.s);
    mix((size_t)k.t);
    mix((size_t)k.u);
    mix((size_t)k.v);
    return h;
  }
};

class DPScheduler {
public:
  DPScheduler(
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
  );

  std::pair<double, std::vector<std::pair<Topology,int>>> synthesize();
  std::pair<double, std::vector<std::pair<Topology,int>>> synthesize_for_k(int k);

  std::vector<Topology> expandSchedulePerStep(
    const std::vector<std::pair<Topology,int>>& schedule,
    int num_steps
  ) const;

private:
  int ringNext(int u) const;
  int ringPrev(int u) const;
  std::vector<int> torusNeighbors(int u) const;

  Topology base_topology() const;

  bool checkReachable(
    const std::vector<std::vector<int>>& adj,
    const std::unordered_map<int, std::unordered_set<int>>& bySource
  ) const;

  std::pair<Topology, double> completion_time(int a, int b);

private:
  std::vector<std::vector<Demand>> steps_;
  int s_;
  int n_;
  int d_;
  double c_;
  double beta_;
  double alpha_;
  double delta_;
  double alpha_r_;
  std::vector<int> dims_;
  std::vector<int> chunksizes_;
  int relaxation_;
  int logging_;
  int rd_;

  std::unordered_map<std::pair<int,int>, std::pair<Topology,double>, PairHash> cache_;
};
