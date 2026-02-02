#!/bin/bash

# CXXFLAGS="-g -O0 -fno-omit-frame-pointer -fno-fast-math -std=c++17"
CXXFLAGS="-O3 -std=c++17"
g++ $CXXFLAGS -I$GUROBI_HOME/include/ -I./   main.cc DPSchedulerPath.cc -L$GUROBI_HOME/lib/ -lgurobi_c++ -lgurobi130 -o synthesize-schedule
