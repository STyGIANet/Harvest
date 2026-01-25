#pragma once

#include <gurobi_c++.h>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <tuple>
#include <utility>
#include <cstddef>
#include <cstdint>

struct Demand {
  int s;
  int t;
  uint64_t bits;
};

struct Edge {
  int u;
  int v;
  bool operator==(const Edge& o) const noexcept { return u == o.u && v == o.v; }
};

struct EdgeHash {
  size_t operator()(const Edge& e) const noexcept {
    return (static_cast<size_t>(static_cast<uint32_t>(e.u)) << 32) ^
           static_cast<size_t>(static_cast<uint32_t>(e.v));
  }
};

using Topology = std::unordered_map<Edge, int, EdgeHash>;

struct SchedulerResult {
  double cost;
  std::vector<std::pair<Topology, int>> schedule;
  double reconf_cost;
  int k;
};

struct PairHash {
  size_t operator()(const std::pair<int,int>& p) const noexcept {
    return (static_cast<size_t>(static_cast<uint32_t>(p.first)) << 32) ^
           static_cast<size_t>(static_cast<uint32_t>(p.second));
  }
};

using Pair = std::pair<int,int>;
using Path = std::vector<Edge>;

struct PathKey {
  int i;
  int s;
  int t;
  int pidx;
  bool operator==(const PathKey& o) const noexcept {
    return i==o.i && s==o.s && t==o.t && pidx==o.pidx;
  }
};

struct PathKeyHash {
  size_t operator()(const PathKey& k) const noexcept {
    size_t h = 1469598103934665603ULL;
    auto mix = [&](size_t x) {
      h ^= x + 0x9e3779b97f4a7c15ULL + (h<<6) + (h>>2);
    };
    mix((size_t)k.i);
    mix((size_t)k.s);
    mix((size_t)k.t);
    mix((size_t)k.pidx);
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
    const std::vector<uint64_t>& chunksizes,
    int relaxation,
    int logging,
    int rd,
    std::string collective
  );

  SchedulerResult synthesize();
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
  Topology base_ring() const;

  bool checkReachable(
    const std::vector<std::vector<int>>& adj,
    const std::unordered_map<int, std::unordered_set<int>>& bySource
  ) const;

  std::vector<int> bfs_parent(const std::vector<std::vector<int>>& adj, int s, int t,
                              const std::unordered_set<Edge, EdgeHash>* bannedEdges,
                              const std::unordered_set<int>* bannedNodes) const;

  bool reconstruct_path_edges(int s, int t, const std::vector<int>& parent, Path& out) const;

  std::vector<Path> k_shortest_paths_yen(
    const std::vector<std::vector<int>>& adj,
    int s, int t,
    int K,
    int maxPathLen
  ) const;

  std::pair<Topology, double> completion_time(int a, int b);
  std::pair<Topology, double> completion_time_all_to_all(int a, int b);
  std::vector<int> torusNeighbors3D(int u) const;
  int kautzLabelLength() const;
  std::vector<int> kautzUnrank(int id, int k) const;
  int kautzRank(const std::vector<int>& x) const;
  std::vector<int> kautzNeighbors(int u) const;
  std::vector<int> expanderNeighbors(int u) const;
  std::vector<int> deBruijnNeighbors(int u) const;
  double getDemandStep(int i);


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
  std::vector<uint64_t> chunksizes_;
  int relaxation_;
  int logging_;
  int rd_;
  std::string collective_;

  std::unordered_map<std::pair<int,int>, std::pair<Topology,double>, PairHash> cache_;
};
