#include "DPScheduler.h"
#include <nlohmann/json.hpp>

#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <regex>

using json = nlohmann::json;

int main(int argc, char* argv[]) {
  if (argc != 11) {
    std::cerr
      << "usage: synthesize-schedule collective.json degree capacity alpha delta "
         "alpha_r logging relaxation rd out.json\n";
    return 1;
  }

  std::string in_file = argv[1];
  int d = std::stoi(argv[2]);
  double c = std::stod(argv[3]);
  double beta = 1.0 / c;
  double alpha = std::stod(argv[4]);
  double delta = std::stod(argv[5]);
  double alpha_r = std::stod(argv[6]);
  int logging = std::stoi(argv[7]);
  int relaxation = std::stoi(argv[8]);
  int rd = std::stoi(argv[9]);
  std::string out_file = argv[10];

  json doc;
  {
    std::ifstream fin(in_file);
    if (!fin) {
      std::cerr << "Failed to open input file: " << in_file << "\n";
      return 1;
    }
    fin >> doc;
  }

  int n = doc.at("n").get<int>();
  std::vector<int> dims = doc.at("dims").get<std::vector<int>>();

  std::vector<std::vector<Demand>> steps;
  std::vector<int> chunksizes;

  auto jsteps = doc.at("steps");
  steps.reserve(jsteps.size());
  chunksizes.reserve(jsteps.size());

  for (const auto& s : jsteps) {
    std::vector<Demand> step;
    for (const auto& dmd : s.at("demand")) {
      int u = dmd[0].get<int>();
      int v = dmd[1].get<int>();
      int m_bits = dmd[2].get<int>() * 8;
      step.push_back(Demand{u, v, m_bits});
    }
    steps.push_back(std::move(step));
    chunksizes.push_back(s.at("chunksize").get<int>() * 8);
  }

  DPScheduler scheduler(
    steps, n, d, c, beta, alpha, delta, alpha_r, dims, chunksizes,
    relaxation, logging, rd
  );

  SchedulerResult res = scheduler.synthesize();
  auto total_reconf_cost = res.reconf_cost;
  auto k = res.k;
  auto stepTopos = scheduler.expandSchedulePerStep(res.schedule, (int)steps.size());
  std::regex re(R"(collective-(.+?)(?=-\d))");
  std::smatch match;
  std::regex_search(in_file, match, re);
  
  json out;
  out["cost"] = res.cost;
  out["num_of_reconfigs"] = k;
  out["alpha_r"] = alpha_r;
  out["collective"] = match[1];
  out["reconf_cost_total"] = total_reconf_cost;
  out["steps"] = json::array();


  for (int i = 0; i < (int)stepTopos.size(); ++i) {
    json entry;
    entry["step"] = i + 1;
    entry["topology"] = json::array();
    for (const auto& kv : stepTopos[i]) {
      const Edge& e = kv.first;
      int k = kv.second;
      entry["topology"].push_back({e.u, e.v, k});
    }
    out["steps"].push_back(std::move(entry));
  }

  {
    std::ofstream fout(out_file);
    if (!fout) {
      std::cerr << "Failed to open output file: " << out_file << "\n";
      return 1;
    }
    fout << out.dump(2) << "\n";
  }

  return 0;
}
