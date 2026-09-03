// Generated/Converted by GPT based on the python implementation of the same.
// dp_schedule.cu
// CUDA conversion of your Python DP with identical CLI and output behavior.
//
// stdout behavior (exactly like Python):
//   - if --printReconf 1:
//       prints per-step edges: "<step-1> <i> <dst>"
//       then prints the reconf list, e.g., "[2, 4]"
//   - else:
//       prints a single integer: int(finalTotalCost * 1e9)
//
// Device-only timing (CUDA events) is written to stderr as:
//   TIMING device_start_ms=0.000000 device_end_ms=<elapsed_ms> completion_ms=<elapsed_ms>
//
// Build: nvcc -O3 -use_fast_math -std=c++17 dp_schedule.cu -o dp_schedule
// Usage: ./dp_schedule -n 16 -m 8000000 --delta 500 --bw 400 --reconf 1

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <string>
#include <cmath>
#include <getopt.h>
#include <limits>
#include <algorithm>
#include <cfloat>

#include <cuda.h>
#include <cuda_runtime.h>

#define CUDA_CHECK(call) \
  do { \
    cudaError_t err__ = (call); \
    if (err__ != cudaSuccess) { \
      fprintf(stderr, "CUDA error %s (%d) at %s:%d: %s\n", \
              #call, static_cast<int>(err__), __FILE__, __LINE__, cudaGetErrorString(err__)); \
      std::exit(1); \
    } \
  } while (0)

// Flattened index: a in [1..S+1], t in [0..S]
__host__ __device__ inline int idxAT(int a, int t, int S) {
  return (a - 1) * (S + 1) + t;
}

// pow2[i] = 2^i for i in [0..s+2]
__global__ void kInitPow2(double* __restrict__ pow2, int s) {
  int i = blockDim.x * blockIdx.x + threadIdx.x;
  int maxI = s + 2;
  if (i <= maxI) pow2[i] = ldexp(1.0, i);
}

// DP[:,0] initialization (a in [1..s+1])
// DP[a][0] = beta*(m/2^a)*((s+1)-a) + delta * (2^(s-a+2) - 1)
__global__ void kInitDP0(double* __restrict__ DP,
                         const double* __restrict__ pow2,
                         int s,
                         double m_bits,
                         double beta,
                         double delta_s) {
  int a = 1 + blockDim.x * blockIdx.x + threadIdx.x;
  if (a > s + 1) return;

  double denom = pow2[a]; // 2^a
  double comm = beta * (m_bits / denom) * ((s + 1) - a);

  double prop = 0.0;
  if (delta_s != 0.0) {
    int exp_idx = (s - a + 2);
    prop = delta_s * (pow2[exp_idx] - 1.0);
  }
  DP[idxAT(a, 0, s)] = comm + prop;
}

// For t>=1: DP[a][t] = min_{b in a+1..s+1} { beta*m/2^a*(b-a) + delta*(2^(b-a+1)-1) + DP[b][t-1] }
// One block per 'a', threads reduce over 'b'.
template<int BLOCK_SIZE>
__global__ void kDP_t(double* __restrict__ DP,
                      int*    __restrict__ NXT,
                      const double* __restrict__ pow2,
                      int s,
                      int t,
                      double m_bits,
                      double beta,
                      double delta_s) {
  int a = 1 + blockIdx.x; // a in [1..s]
  if (a > s) return;

  double denom = pow2[a];
  double coeff = beta * (m_bits / denom);

  double best_val = DBL_MAX;
  int best_b = -1;

  __shared__ double s_val[BLOCK_SIZE];
  __shared__ int    s_arg[BLOCK_SIZE];

  for (int b = a + 1 + threadIdx.x; b <= s + 1; b += BLOCK_SIZE) {
    double comm = coeff * double(b - a);

    double prop = 0.0;
    if (delta_s != 0.0) {
      int exp_idx = (b - a + 1);
      prop = delta_s * (pow2[exp_idx] - 1.0);
    }

    double val = comm + prop + DP[idxAT(b, t - 1, s)];
    if (val < best_val) { best_val = val; best_b = b; }
  }

  s_val[threadIdx.x] = best_val;
  s_arg[threadIdx.x] = best_b;
  __syncthreads();

  // reduction to find min
  for (int offset = BLOCK_SIZE >> 1; offset > 0; offset >>= 1) {
    if (threadIdx.x < offset) {
      double ov = s_val[threadIdx.x + offset];
      int    ob = s_arg[threadIdx.x + offset];
      if (ov < s_val[threadIdx.x]) {
        s_val[threadIdx.x] = ov;
        s_arg[threadIdx.x] = ob;
      }
    }
    __syncthreads();
  }

  if (threadIdx.x == 0) {
    DP[idxAT(a, t, s)] = s_val[0];
    NXT[idxAT(a, t, s)] = s_arg[0];
  }
}

struct Args {
  int n = -1;
  double m_bytes = 1.0;
  double delta_ns = 0.0;
  double bw_gbps = 0.0;
  double reconf_ns = 0.0;
  int printReconf = 0;
};

static void usageAndExit(const char* prog) {
  fprintf(stderr,
    "Usage: %s -n <nodes> [-m <bytes>] [--delta <ns>] [--bw <Gbps>] [--reconf <ns>] [--printReconf <0|1>]\n",
    prog);
  std::exit(1);
}

static Args parseArgs(int argc, char** argv) {
  Args a;
  static struct option long_opts[] = {
    {"delta",        required_argument, 0,  1},
    {"bw",           required_argument, 0,  2},
    {"reconf",       required_argument, 0,  3},
    {"printReconf",  required_argument, 0,  4},
    {0,0,0,0}
  };
  int c;
  while ((c = getopt_long(argc, argv, "n:m:", long_opts, nullptr)) != -1) {
    switch (c) {
      case 'n': a.n = std::atoi(optarg); break;
      case 'm': a.m_bytes = std::atof(optarg); break;
      case 1: a.delta_ns = std::atof(optarg); break;
      case 2: a.bw_gbps  = std::atof(optarg); break;
      case 3: a.reconf_ns = std::atof(optarg); break;
      case 4: a.printReconf = std::atoi(optarg); break;
      default: usageAndExit(argv[0]);
    }
  }
  if (a.n <= 1) {
    fprintf(stderr, "Use at least 2 nodes.\n");
    usageAndExit(argv[0]);
  }
  return a;
}

int main(int argc, char** argv) {
  Args args = parseArgs(argc, argv);
  printf("n\tcost\ttimeMicro\tnumReconfs\n");
  for (int n = 4; n<=1024; n=n*2){
    args.n = n;
      int s = static_cast<int>(std::ceil(std::log2((double)args.n)));
      if (s < 1) {
        // match Python: message + exit
        printf("Use at least 2 nodes, and n as a power of 2.\n");
        return 0;
      }

      const double delta_s  = args.delta_ns * 1e-9;
      const double beta     = (args.bw_gbps > 0.0) ? (1.0 / (args.bw_gbps * 1e9)) : std::numeric_limits<double>::infinity();
      const double m_bits   = args.m_bytes * 8.0;
      const double reconf_s = args.reconf_ns * 1e-9;

      // device buffers
      const int rows_a = (s + 2);
      const int cols_t = (s + 1);
      const int DP_elems = rows_a * cols_t;

      double* d_DP = nullptr;
      int*    d_NXT = nullptr;
      double* d_pow2 = nullptr;

      CUDA_CHECK(cudaMalloc(&d_DP,   DP_elems * sizeof(double)));
      CUDA_CHECK(cudaMalloc(&d_NXT,  DP_elems * sizeof(int)));
      CUDA_CHECK(cudaMalloc(&d_pow2, (s + 3) * sizeof(double)));

      // pow2
      {
        int threads = 128;
        int blocks  = ((s + 2) + threads) / threads;
        kInitPow2<<<blocks, threads>>>(d_pow2, s);
        CUDA_CHECK(cudaPeekAtLastError());
      }

      // DP[:,0]
      {
        int threads = 128;
        int blocks  = ((s + 1) + threads - 1) / threads;
        kInitDP0<<<blocks, threads>>>(d_DP, d_pow2, s, m_bits, beta, delta_s);
        CUDA_CHECK(cudaPeekAtLastError());
      }

      // device-only timing
      cudaEvent_t evStart, evStop;
      CUDA_CHECK(cudaEventCreate(&evStart));
      CUDA_CHECK(cudaEventCreate(&evStop));
      CUDA_CHECK(cudaEventRecord(evStart));

      // DP layers t=1..s
      constexpr int BLOCK_SIZE = 256;
      dim3 gridDP(s, 1, 1);     // one block per a
      dim3 blockDP(BLOCK_SIZE);

      for (int t = 1; t <= s; ++t) {
        kDP_t<BLOCK_SIZE><<<gridDP, blockDP>>>(d_DP, d_NXT, d_pow2, s, t, m_bits, beta, delta_s);
        CUDA_CHECK(cudaPeekAtLastError());
      }

      CUDA_CHECK(cudaEventRecord(evStop));
      CUDA_CHECK(cudaEventSynchronize(evStop));

      float elapsed_ms = 0.0f;
      CUDA_CHECK(cudaEventElapsedTime(&elapsed_ms, evStart, evStop));

      // copy back
      std::vector<double> h_DP(DP_elems, 0.0);
      std::vector<int>    h_NXT(DP_elems, -1);
      CUDA_CHECK(cudaMemcpy(h_DP.data(), d_DP, DP_elems * sizeof(double), cudaMemcpyDeviceToHost));
      CUDA_CHECK(cudaMemcpy(h_NXT.data(), d_NXT, DP_elems * sizeof(int),    cudaMemcpyDeviceToHost));

      // free device
      CUDA_CHECK(cudaFree(d_DP));
      CUDA_CHECK(cudaFree(d_NXT));
      CUDA_CHECK(cudaFree(d_pow2));
      CUDA_CHECK(cudaEventDestroy(evStart));
      CUDA_CHECK(cudaEventDestroy(evStop));

      // choose best k
      double best_total = std::numeric_limits<double>::infinity();
      int best_k = 0;
      for (int k = 0; k <= s; ++k) {
        double base = h_DP[idxAT(1, k, s)];
        double total = base + (double)k * reconf_s;
        if (total < best_total) { best_total = total; best_k = k; }
      }

      // reconstruct reconf list
      std::vector<int> reconfList;
      {
        int a = 1, t = best_k;
        while (t > 0) {
          int b = h_NXT[idxAT(a, t, s)];
          if (b <= 0) break;
          if (b <= s) reconfList.push_back(b);
          a = b;
          --t;
        }
      }

      // print timing to stderr (doesn't affect stdout contract)
      // fprintf(stderr,
      //         "TIMING device_start_ms=%.6f device_end_ms=%.6f completion_ms=%.6f\n",
      //         0.0, (double)elapsed_ms, (double)elapsed_ms);

      // stdout behavior EXACTLY like your Python:
      if (args.printReconf == 1) {
        int currState = 1;
        std::vector<char> isReconf(s+2, 0);
        for (int r : reconfList) if (r >= 1 && r <= s) isReconf[r] = 1;

        for (int step = 1; step <= s; ++step) {
          if (isReconf[step]) currState = step;
          int shift = 1 << (currState - 1);
          for (int i = 0; i < args.n; ++i) {
            int dst = (i + shift) % args.n;
            // steps indexed from 0 like your Python print
            printf("%d %d %d\n", step - 1, i, dst);
          }
        }
        // reconf list
        printf("[");
        for (size_t i = 0; i < reconfList.size(); ++i) {
          printf("%d", reconfList[i]);
          if (i + 1 < reconfList.size()) printf(", ");
        }
        printf("]\n");
      } else {
        // int(finalTotalCost * 1e9)
        long long ns = (long long)(best_total * 1e9);
        printf("%d\t%lld\t%.6f\t%zu\n", n, ns, (double)elapsed_ms*1e3, reconfList.size());
      }
  }

  return 0;
}
