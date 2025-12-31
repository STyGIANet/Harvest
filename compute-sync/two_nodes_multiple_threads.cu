#include <stdio.h>
#include <stdlib.h>
#include <cuda_runtime.h>

#define CHECK_CUDA(call)                                                     \
  do {                                                                       \
    cudaError_t _e = (call);                                                 \
    if (_e != cudaSuccess) {                                                 \
      fprintf(stderr, "CUDA error %s:%d: %s\n", __FILE__, __LINE__,          \
              cudaGetErrorString(_e));                                       \
      exit(1);                                                               \
    }                                                                        \
  } while (0)

__global__ void fairClaimKernel(
    int *output,
    int *sharedValue,               // global counter (GPU0 memory)
    int *perDeviceCounts,           // per-GPU counts (GPU0 memory)
    unsigned long long *perGPUStartClocks,
    int *chosenDeviceId,
    unsigned long long *start_clock,
    unsigned long long *end_clock,
    int quotaPerGPU,
    int maxOutPerDevice,
    int deviceId
) {
    // Record per-GPU start time once
    if (threadIdx.x == 0) {
        perGPUStartClocks[deviceId] = clock64();
        __threadfence_system();
    }

    while (true) {
        // Enforce per-GPU quota first (fairness)
        int localCount = atomicAdd_system(&perDeviceCounts[deviceId], 0);
        if (localCount >= quotaPerGPU) {
            break;
        }

        // Try to claim global work
        int old = atomicAdd_system(sharedValue, -1);

        // No work left → exit
        if (old <= 0) {
            // optional cleanup so counter doesn't drift negative
            atomicAdd_system(sharedValue, 1);
            break;
        }

        // Successfully claimed one unit
        int outIdx = atomicAdd_system(&perDeviceCounts[deviceId], 1);
        if (outIdx < maxOutPerDevice) {
            output[outIdx] = old;
        }

        // If this was the last item, record timing exactly once
        if (old == 1) {
            int prev = atomicCAS_system(chosenDeviceId, -1, deviceId);
            if (prev == -1) {
                *start_clock = perGPUStartClocks[deviceId];
                *end_clock   = clock64();
                __threadfence_system();
            }
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 3) {
        printf("Usage: %s <total_operations> <threads_per_block>\n", argv[0]);
        return 1;
    }

    int totalOperations = atoi(argv[1]);
    int threadsPerBlock = atoi(argv[2]);

    if (totalOperations <= 0 || threadsPerBlock <= 0 || threadsPerBlock > 1024) {
        printf("Invalid arguments.\n");
        return 1;
    }

    int deviceCount = 0;
    CHECK_CUDA(cudaGetDeviceCount(&deviceCount));
    if (deviceCount < 2) {
        printf("Need at least 2 GPUs.\n");
        return 1;
    }

    const int numGPUs = 2;
    int gpuIds[numGPUs] = {0, 1};

    printf("Detected %d GPUs, using GPU 0 and GPU 1\n", deviceCount);
    printf("totalOperations=%d, threadsPerBlock=%d\n",
           totalOperations, threadsPerBlock);

    // Fair quota per GPU
    int quotaPerGPU = (totalOperations + numGPUs - 1) / numGPUs;
    int maxOutPerDevice = quotaPerGPU;

    printf("Quota per GPU = %d\n", quotaPerGPU);

    // Allocate shared state on GPU0
    CHECK_CUDA(cudaSetDevice(0));

    int *d_sharedValue;
    int *d_perDeviceCounts;
    int *d_chosenDeviceId;
    unsigned long long *d_perGPUStartClocks;
    unsigned long long *d_start_clock, *d_end_clock;

    CHECK_CUDA(cudaMalloc(&d_sharedValue, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_perDeviceCounts, numGPUs * sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_chosenDeviceId, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_perGPUStartClocks, numGPUs * sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_start_clock, sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_end_clock, sizeof(unsigned long long)));

    CHECK_CUDA(cudaMemcpy(d_sharedValue, &totalOperations,
                          sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemset(d_perDeviceCounts, 0, numGPUs * sizeof(int)));

    int minusOne = -1;
    CHECK_CUDA(cudaMemcpy(d_chosenDeviceId, &minusOne,
                          sizeof(int), cudaMemcpyHostToDevice));

    // Enable P2P both directions
    CHECK_CUDA(cudaSetDevice(0));
    cudaDeviceEnablePeerAccess(1, 0);
    CHECK_CUDA(cudaSetDevice(1));
    cudaDeviceEnablePeerAccess(0, 0);

    // Allocate output buffers per GPU
    int *d_outputs[numGPUs];
    for (int i = 0; i < numGPUs; i++) {
        CHECK_CUDA(cudaSetDevice(gpuIds[i]));
        CHECK_CUDA(cudaMalloc(&d_outputs[i],
                              maxOutPerDevice * sizeof(int)));
        CHECK_CUDA(cudaMemset(d_outputs[i], 0,
                              maxOutPerDevice * sizeof(int)));
    }

    // Launch kernels
    for (int i = 0; i < numGPUs; i++) {
        CHECK_CUDA(cudaSetDevice(gpuIds[i]));
        fairClaimKernel<<<1, threadsPerBlock>>>(
            d_outputs[i],
            d_sharedValue,
            d_perDeviceCounts,
            d_perGPUStartClocks,
            d_chosenDeviceId,
            d_start_clock,
            d_end_clock,
            quotaPerGPU,
            maxOutPerDevice,
            i   // logical deviceId
        );
        CHECK_CUDA(cudaGetLastError());
    }

    // Synchronize
    for (int i = 0; i < numGPUs; i++) {
        CHECK_CUDA(cudaSetDevice(gpuIds[i]));
        CHECK_CUDA(cudaDeviceSynchronize());
    }

    // Read results
    int h_counts[numGPUs];
    CHECK_CUDA(cudaSetDevice(0));
    CHECK_CUDA(cudaMemcpy(h_counts, d_perDeviceCounts,
                          numGPUs * sizeof(int), cudaMemcpyDeviceToHost));

    printf("GPU0 claimed %d, GPU1 claimed %d (sum=%d)\n",
           h_counts[0], h_counts[1], h_counts[0] + h_counts[1]);

    // Timing info
    int h_chosen;
    unsigned long long h_start, h_end;
    CHECK_CUDA(cudaMemcpy(&h_chosen, d_chosenDeviceId,
                          sizeof(int), cudaMemcpyDeviceToHost));
    CHECK_CUDA(cudaMemcpy(&h_start, d_start_clock,
                          sizeof(unsigned long long), cudaMemcpyDeviceToHost));
    CHECK_CUDA(cudaMemcpy(&h_end, d_end_clock,
                          sizeof(unsigned long long), cudaMemcpyDeviceToHost));

    printf("\n--- Timing ---\n");
    printf("chosenDeviceId = %d\n", h_chosen);
    printf("start_clock = %llu\n", h_start);
    printf("end_clock   = %llu\n", h_end);

    if (h_chosen >= 0) {
        int clockRateKHz;
        CHECK_CUDA(cudaDeviceGetAttribute(
            &clockRateKHz, cudaDevAttrClockRate, gpuIds[h_chosen]));
        double ms = (double)(h_end - h_start) / (clockRateKHz * 1000.0);
        printf("elapsed time = %.6f ms\n", ms);
    }

    return 0;
}
