#!/bin/bash

g++ -O3 -std=c++17 -I./gurobi1300/linux64/include/ -I./   main.cc DPScheduler.cc -L./gurobi1300/linux64/lib/ -lgurobi_c++ -lgurobi130 -o synthesize-schedule
