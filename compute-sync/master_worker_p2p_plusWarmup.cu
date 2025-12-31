//nvcc -O3 -std=c++17 master_worker_p2p_plusWarmup.cu -o master_worker_p2p_plusWarmup

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cuda_runtime.h>

#define CUDA_CHECK(call) do {                                     \
  cudaError_t err = (call);                                       \
  if (err != cudaSuccess) {                                       \
    fprintf(stderr, "CUDA error %s:%d: %s\n",                      \
            __FILE__, __LINE__, cudaGetErrorString(err));         \
    std::exit(EXIT_FAILURE);                                     \
  }                                                               \
} while (0)

struct Result {
  unsigned long long cycles;
  double ns_total;
  double ns_avg_per_iter;
};

__global__ void warmup_kernel() { }

__global__ void master_worker_kernel(
    int device_id,
    volatile uint32_t* flags,   // length L, lives on MASTER GPU memory
    int L,
    int iters_measured,         // number of measured iterations
    Result* out,                // only valid on master
    int clock_khz)              // only valid on master
{
  // We run one extra iteration internally (warm-up) to remove kernel-start skew.
  const int iters_total = iters_measured + 1;

  /* ===================== MASTER (GPU0) ===================== */
  if (device_id == 0) {
    if (blockIdx.x != 0 || threadIdx.x != 0) return;

    // ---- warm-up iteration (not timed) ----
    while (true) {
      int cnt = 0;
      #pragma unroll 1
      for (int i = 0; i < L; i++) cnt += (flags[i] != 0);
      if (cnt == L) break;
    }
    // reset all flags
    #pragma unroll 1
    for (int i = 0; i < L; i++) flags[i] = 0;
    __threadfence_system();

    // ---- timed iterations ----
    unsigned long long start = clock64();

    for (int it = 0; it < iters_measured; it++) {
      // wait until all L workers have set their flag
      while (true) {
        int cnt = 0;
        #pragma unroll 1
        for (int i = 0; i < L; i++) cnt += (flags[i] != 0);
        if (cnt == L) break;
      }

      // reset for next iteration
      #pragma unroll 1
      for (int i = 0; i < L; i++) flags[i] = 0;
      __threadfence_system();
    }

    unsigned long long end = clock64();
    unsigned long long elapsed = end - start;

    out->cycles = elapsed;
    out->ns_total = (double)elapsed * 1.0e6 / (double)clock_khz;
    out->ns_avg_per_iter = out->ns_total / (double)iters_measured;
    return;
  }

  /* ===================== WORKER (GPU1) ===================== */
  int tid = blockIdx.x * blockDim.x + threadIdx.x;
  if (tid >= L) return;

  // Each logical worker participates in iters_total iterations.
  for (int it = 0; it < iters_total; it++) {
    // Ensure we start this iteration only when our flag is 0 (master has reset)
    while (flags[tid] != 0) { }

    // Signal completion for this iteration
    flags[tid] = 1;
    __threadfence_system();

    // Wait until master observes & resets us back to 0
    while (flags[tid] != 0) { }
  }
}

int main(int argc, char** argv) {
  if (argc < 3) {
    fprintf(stderr, "Usage: %s <L_logical_workers> <iters_measured> [block_dim]\n", argv[0]);
    fprintf(stderr, "Example: %s 1024 10000 256\n", argv[0]);
    return EXIT_FAILURE;
  }

  int L = std::atoi(argv[1]);
  int iters_measured = std::atoi(argv[2]);
  int block_dim = (argc >= 4) ? std::atoi(argv[3]) : 256;

  if (L <= 0 || iters_measured <= 0 || block_dim <= 0) {
    fprintf(stderr, "Invalid arguments. Require L>0, iters_measured>0, block_dim>0.\n");
    return EXIT_FAILURE;
  }

  int device_count = 0;
  CUDA_CHECK(cudaGetDeviceCount(&device_count));
  if (device_count < 2) {
    fprintf(stderr, "Need at least 2 GPUs.\n");
    return EXIT_FAILURE;
  }

  int masterDev = 0;
  int workerDev = 1;

  int canP2P = 0;
  CUDA_CHECK(cudaDeviceCanAccessPeer(&canP2P, workerDev, masterDev));
  if (!canP2P) {
    fprintf(stderr, "P2P access from GPU%d -> GPU%d not supported on this system/topology.\n",
            workerDev, masterDev);
    return EXIT_FAILURE;
  }

  // Get master SM clock rate (kHz) for clock64 conversion.
  int clock_khz = 0;
  CUDA_CHECK(cudaDeviceGetAttribute(&clock_khz, cudaDevAttrClockRate, masterDev));

  // Allocate flags + result on MASTER GPU memory.
  CUDA_CHECK(cudaSetDevice(masterDev));
  uint32_t* d_flags = nullptr;
  Result* d_out = nullptr;

  CUDA_CHECK(cudaMalloc(&d_flags, (size_t)L * sizeof(uint32_t)));
  CUDA_CHECK(cudaMemset(d_flags, 0, (size_t)L * sizeof(uint32_t)));

  CUDA_CHECK(cudaMalloc(&d_out, sizeof(Result)));
  CUDA_CHECK(cudaMemset(d_out, 0, sizeof(Result)));

  // Enable peer access on WORKER GPU so it can write into master memory.
  CUDA_CHECK(cudaSetDevice(workerDev));
  CUDA_CHECK(cudaDeviceEnablePeerAccess(masterDev, 0));

  // Warm up both GPUs (context, clocks, etc.)
  CUDA_CHECK(cudaSetDevice(masterDev));
  warmup_kernel<<<1,1>>>();
  CUDA_CHECK(cudaDeviceSynchronize());

  CUDA_CHECK(cudaSetDevice(workerDev));
  warmup_kernel<<<1,1>>>();
  CUDA_CHECK(cudaDeviceSynchronize());

  // Launch WORKER kernel first (it will spin/wait safely).
  CUDA_CHECK(cudaSetDevice(workerDev));
  int grid = (L + block_dim - 1) / block_dim;
  master_worker_kernel<<<grid, block_dim>>>(
      /*device_id=*/1,
      d_flags, L,
      iters_measured,
      nullptr, 0);
  CUDA_CHECK(cudaGetLastError());

  // Launch MASTER kernel (times only steady-state iterations after an internal warm-up).
  CUDA_CHECK(cudaSetDevice(masterDev));
  master_worker_kernel<<<1, 1>>>(
      /*device_id=*/0,
      d_flags, L,
      iters_measured,
      d_out, clock_khz);
  CUDA_CHECK(cudaGetLastError());

  // Synchronize both devices.
  CUDA_CHECK(cudaSetDevice(workerDev));
  CUDA_CHECK(cudaDeviceSynchronize());
  CUDA_CHECK(cudaSetDevice(masterDev));
  CUDA_CHECK(cudaDeviceSynchronize());

  // Read result.
  Result h{};
  CUDA_CHECK(cudaMemcpy(&h, d_out, sizeof(Result), cudaMemcpyDeviceToHost));

  printf("Master GPU: %d | Worker GPU: %d\n", masterDev, workerDev);
  printf("L (logical workers): %d | block_dim: %d | grid(blocks): %d\n", L, block_dim, grid);
  printf("Measured iterations: %d (plus 1 warm-up iter inside kernel)\n", iters_measured);
  printf("Master clock: %d kHz\n", clock_khz);
  printf("Total time: %.3f ns\n", h.ns_total);
  printf("Avg per iteration: %.3f ns  (%.6f us)\n", h.ns_avg_per_iter, h.ns_avg_per_iter / 1e3);

  CUDA_CHECK(cudaFree(d_flags));
  CUDA_CHECK(cudaFree(d_out));
  return EXIT_SUCCESS;
}
