//nvcc -O3 -std=c++17 single_kernel_p2p_master_worker.cu -o p2p_sync

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
  double ns;
};

__global__ void master_worker_kernel(
    int device_id,
    volatile uint32_t* flags,
    int L,
    Result* out,
    int clock_khz)
{
  /* ===================== MASTER GPU ===================== */
  if (device_id == 0) {
    if (blockIdx.x != 0 || threadIdx.x != 0) return;

    unsigned long long start = clock64();

    while (true) {
      int cnt = 0;
      //#pragma unroll 1
      for (int i = 0; i < L; i++) {
        cnt += (flags[i] != 0);
      }
      if (cnt == L){
        printf("L is: %d\n", L);
        printf("cnt is: %d\n", cnt);
        break;
      }

      // avoid saturating the interconnect
      //__nanosleep(64);
    }

    unsigned long long end = clock64();
    unsigned long long elapsed = end - start;

    out->cycles = elapsed;
    out->ns = (double)elapsed * 1.0e6 / (double)clock_khz;
    return;
  }

  /* ===================== WORKER GPU ===================== */
  int tid = blockIdx.x * blockDim.x + threadIdx.x;
  if (tid >= L) return;

  // P2P store into master GPU memory
  flags[tid] = 1;

  // ensure visibility across GPUs
  __threadfence_system();
}

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "Usage: %s <logical_threads_L> [block_dim]\n", argv[0]);
    return EXIT_FAILURE;
  }

  int L = std::atoi(argv[1]);
  int block_dim = (argc >= 3) ? std::atoi(argv[2]) : 256;

  if (L <= 0 || block_dim <= 0) {
    fprintf(stderr, "Invalid arguments\n");
    return EXIT_FAILURE;
  }

  int device_count = 0;
  CUDA_CHECK(cudaGetDeviceCount(&device_count));
  if (device_count < 2) {
    fprintf(stderr, "This program requires at least 2 GPUs\n");
    return EXIT_FAILURE;
  }

  int masterDev = 0;
  int workerDev = 1;

  int canAccess = 0;
  CUDA_CHECK(cudaDeviceCanAccessPeer(&canAccess, workerDev, masterDev));
  if (!canAccess) {
    fprintf(stderr, "P2P access from GPU %d to GPU %d not supported\n",
            workerDev, masterDev);
    return EXIT_FAILURE;
  }

  /* ===================== MASTER SETUP ===================== */
  CUDA_CHECK(cudaSetDevice(masterDev));

  int clock_khz = 0;
  CUDA_CHECK(cudaDeviceGetAttribute(&clock_khz, cudaDevAttrClockRate, masterDev));

  uint32_t* d_flags = nullptr;
  Result* d_out = nullptr;

  CUDA_CHECK(cudaMalloc(&d_flags, (size_t)L * sizeof(uint32_t)));
  CUDA_CHECK(cudaMemset(d_flags, 0, (size_t)L * sizeof(uint32_t)));

  CUDA_CHECK(cudaMalloc(&d_out, sizeof(Result)));
  CUDA_CHECK(cudaMemset(d_out, 0, sizeof(Result)));

  /* ===================== WORKER SETUP ===================== */
  CUDA_CHECK(cudaSetDevice(workerDev));
  CUDA_CHECK(cudaDeviceEnablePeerAccess(masterDev, 0));

  /* ===================== KERNEL LAUNCHES ===================== */

  // Launch worker kernel
  CUDA_CHECK(cudaSetDevice(workerDev));
  int grid = (L + block_dim - 1) / block_dim;
  master_worker_kernel<<<grid, block_dim>>>(
      /*device_id=*/1,
      d_flags,
      L,
      nullptr,
      0);

  // Launch master kernel first (it will spin)
  CUDA_CHECK(cudaSetDevice(masterDev));
  master_worker_kernel<<<1, 1>>>(
      /*device_id=*/0,
      d_flags,
      L,
      d_out,
      clock_khz);


  /* ===================== CORRECT SYMMETRIC SYNC ===================== */
  CUDA_CHECK(cudaSetDevice(workerDev));
  CUDA_CHECK(cudaDeviceSynchronize());

  CUDA_CHECK(cudaSetDevice(masterDev));
  CUDA_CHECK(cudaDeviceSynchronize());

  /* ===================== READ RESULT ===================== */
  Result h{};
  CUDA_CHECK(cudaMemcpy(&h, d_out, sizeof(Result),
                        cudaMemcpyDeviceToHost));

  printf("Master GPU: %d | Worker GPU: %d\n", masterDev, workerDev);
  printf("Logical threads (L): %d | block_dim: %d\n", L, block_dim);
  printf("Elapsed cycles: %llu\n",
         (unsigned long long)h.cycles);
  printf("Elapsed time: %.3f ns (%.6f ms)\n",
         h.ns, h.ns / 1e6);

  /* ===================== CLEANUP ===================== */
  CUDA_CHECK(cudaFree(d_flags));
  CUDA_CHECK(cudaFree(d_out));

  return EXIT_SUCCESS;
}
