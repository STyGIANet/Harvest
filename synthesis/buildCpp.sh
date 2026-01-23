#!/bin/bash

g++ -O3 -std=c++17 -I$GUROBI_HOME/include/ -I./   main.cc DPSchedulerPath.cc -L$GUROBI_HOME/lib/ -lgurobi_c++ -lgurobi130 -o synthesize-schedule
