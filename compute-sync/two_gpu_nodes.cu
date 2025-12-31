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

__global__ void p2pKernel(
    int *output,
    int *ticketCounter,
    int *turn,
    int *sharedValue,
    unsigned long long *start_clock,
    unsigned long long *end_clock,
    unsigned long long *perGPUStartClocks,
    int *chosenDeviceId,
    int *perDeviceCounts,     // NEW: shared counts array [numGPUs]
    int maxOutPerDevice,      // NEW: bounds for output buffer
    int deviceId
) {
    // One start clock per device (recorded once per GPU)
    if (threadIdx.x == 0) {
        perGPUStartClocks[deviceId] = clock64();
        __threadfence_system();
    }

    while (true) {
        int currentVal = atomicAdd_system(sharedValue, 0);
        if (currentVal <= 0) break;

        // Parity check (kept as-is)
        bool shouldEnter = false;
        if ((deviceId % 2 == 0) && (currentVal % 2 == 0)) shouldEnter = true;
        else if ((deviceId % 2 != 0) && (currentVal % 2 != 0)) shouldEnter = true;
        if (!shouldEnter) continue;

        int myTicket = atomicAdd_system(ticketCounter, 1);
        __threadfence_system();

        while (atomicAdd_system(turn, 0) != myTicket) {
            __threadfence_system();
        }

        int newVal = -1;
        currentVal = atomicAdd_system(sharedValue, 0);
        if (currentVal > 0) {
            newVal = atomicAdd_system(sharedValue, -1);
            __threadfence_system();

            // NEW: thread-safe output indexing (works for many threads later)
            int outIdx = atomicAdd_system(&perDeviceCounts[deviceId], 1);
            if (outIdx < maxOutPerDevice) {
                output[outIdx] = newVal;
            }

            if (newVal == 1) {
                *chosenDeviceId = deviceId;
                *start_clock = perGPUStartClocks[deviceId];
                *end_clock = clock64();
                __threadfence_system();
            }
        }

        atomicAdd_system(turn, 1);
        __threadfence_system();
    }
}

int main(int argc, char **argv) {
    if (argc != 2) {
        printf("Usage: %s <total_operations>\n", argv[0]);
        return 1;
    }

    int totalOperations = atoi(argv[1]);
    if (totalOperations <= 0) {
        printf("Total operations must be > 0.\n");
        return 1;
    }

    int deviceCount = 0;
    CHECK_CUDA(cudaGetDeviceCount(&deviceCount));
    if (deviceCount < 2) {
        printf("At least two GPUs are required.\n");
        return 1;
    }

    // Force exactly two GPUs: device 0 and 1
    const int numGPUs = 2;
    int gpuIds[numGPUs] = {0, 1};

    printf("Detected %d CUDA devices. Using GPUs %d and %d only.\n",
           deviceCount, gpuIds[0], gpuIds[1]);

    // For now: 1 thread per GPU. Later: threadsPerGPU = totalOperations / numGPUs (or ceil)
    int blocksPerGPU = 1;
    int threadsPerGPU = 1;

    // Allocate enough output room per GPU (ceil(total/2) + slack)
    // 16 is slack (padding)
    int maxOutPerDevice = totalOperations / numGPUs;

    printf("Running with %d total operations.\n", totalOperations);
    printf("Launch config per GPU: blocks=%d, threads=%d\n", blocksPerGPU, threadsPerGPU);
    printf("Output capacity per GPU: %d\n", maxOutPerDevice);

    // Allocate shared state on device 0
    CHECK_CUDA(cudaSetDevice(gpuIds[0]));

    int *d_ticketCounter = nullptr, *d_turn = nullptr, *d_sharedValue = nullptr;
    int *d_chosenDeviceId = nullptr, *d_perDeviceCounts = nullptr;
    unsigned long long *d_start_clock = nullptr, *d_end_clock = nullptr, *d_perGPUStartClocks = nullptr;

    CHECK_CUDA(cudaMalloc(&d_ticketCounter, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_turn, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_sharedValue, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_chosenDeviceId, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_start_clock, sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_end_clock, sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_perGPUStartClocks, numGPUs * sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_perDeviceCounts, numGPUs * sizeof(int)));

    int zero = 0, minusOne = -1;
    CHECK_CUDA(cudaMemcpy(d_ticketCounter, &zero, sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(d_turn, &zero, sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(d_sharedValue, &totalOperations, sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(d_chosenDeviceId, &minusOne, sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemset(d_perGPUStartClocks, 0, numGPUs * sizeof(unsigned long long)));
    CHECK_CUDA(cudaMemset(d_perDeviceCounts, 0, numGPUs * sizeof(int)));

    // Enable peer access from GPU 1 -> GPU 0 (so GPU1 can touch device0 allocations)
    CHECK_CUDA(cudaSetDevice(gpuIds[1]));
    int canAccessPeer = 0;
    CHECK_CUDA(cudaDeviceCanAccessPeer(&canAccessPeer, gpuIds[1], gpuIds[0]));
    if (!canAccessPeer) {
        printf("ERROR: GPU %d cannot access GPU %d memory (no P2P). This program needs a fallback path.\n",
               gpuIds[1], gpuIds[0]);
        return 1;
    }
    CHECK_CUDA(cudaDeviceEnablePeerAccess(gpuIds[0], 0));

    // Allocate output buffers on each GPU (local allocations)
    int *d_outputs[numGPUs] = {nullptr, nullptr};

    for (int i = 0; i < numGPUs; i++) {
        CHECK_CUDA(cudaSetDevice(gpuIds[i]));
        CHECK_CUDA(cudaMalloc(&d_outputs[i], maxOutPerDevice * sizeof(int)));
        CHECK_CUDA(cudaMemset(d_outputs[i], 0, maxOutPerDevice * sizeof(int)));
    }

    // Launch kernels on both GPUs, passing pointers allocated on GPU0
    for (int i = 0; i < numGPUs; i++) {
        int dev = gpuIds[i];
        CHECK_CUDA(cudaSetDevice(dev));
        p2pKernel<<<blocksPerGPU, threadsPerGPU>>>(
            d_outputs[i],
            d_ticketCounter,
            d_turn,
            d_sharedValue,
            d_start_clock,
            d_end_clock,
            d_perGPUStartClocks,
            d_chosenDeviceId,
            d_perDeviceCounts,
            maxOutPerDevice,
            /*deviceId=*/i   // IMPORTANT: logical id 0 or 1, not necessarily cuda device ordinal
        );
        CHECK_CUDA(cudaGetLastError());
    }

    // Sync both GPUs
    for (int i = 0; i < numGPUs; i++) {
        CHECK_CUDA(cudaSetDevice(gpuIds[i]));
        CHECK_CUDA(cudaDeviceSynchronize());
    }

    // Copy counts back (counts live on GPU0)
    int h_counts[numGPUs] = {0, 0};
    CHECK_CUDA(cudaSetDevice(gpuIds[0]));
    CHECK_CUDA(cudaMemcpy(h_counts, d_perDeviceCounts, numGPUs * sizeof(int), cudaMemcpyDeviceToHost));

    // Copy outputs back based on actual counts
    int *h_out0 = (int*)malloc(h_counts[0] * sizeof(int));
    int *h_out1 = (int*)malloc(h_counts[1] * sizeof(int));

    CHECK_CUDA(cudaSetDevice(gpuIds[0]));
    CHECK_CUDA(cudaMemcpy(h_out0, d_outputs[0], h_counts[0] * sizeof(int), cudaMemcpyDeviceToHost));

    CHECK_CUDA(cudaSetDevice(gpuIds[1]));
    CHECK_CUDA(cudaMemcpy(h_out1, d_outputs[1], h_counts[1] * sizeof(int), cudaMemcpyDeviceToHost));

    for (int t = 0; t < h_counts[0]; t++) {
        printf("GPU 0 wrote[%d] = %d\n", t, h_out0[t]);
    }
    for (int t = 0; t < h_counts[1]; t++) {
        printf("GPU 1 wrote[%d] = %d\n", t, h_out1[t]);
    }

    // Timing and chosenDeviceId from GPU0
    int h_chosenDeviceId = -1;
    unsigned long long h_start_clock = 0, h_end_clock = 0;

    CHECK_CUDA(cudaSetDevice(gpuIds[0]));
    CHECK_CUDA(cudaMemcpy(&h_chosenDeviceId, d_chosenDeviceId, sizeof(int), cudaMemcpyDeviceToHost));
    CHECK_CUDA(cudaMemcpy(&h_start_clock, d_start_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost));
    CHECK_CUDA(cudaMemcpy(&h_end_clock, d_end_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost));

    int clockRateKHz = 0;
    CHECK_CUDA(cudaDeviceGetAttribute(&clockRateKHz, cudaDevAttrClockRate, gpuIds[h_chosenDeviceId]));

    double elapsed_ms = 0.0;
    if (h_chosenDeviceId >= 0 && h_end_clock >= h_start_clock) {
        elapsed_ms = (double)(h_end_clock - h_start_clock) / (clockRateKHz * 1000.0);
    }

    printf("\n--- Timing Info ---\n");
    printf("Chosen GPU (logical id): %d\n", h_chosenDeviceId);
    printf("Start clock64: %llu\n", h_start_clock);
    printf("End clock64:   %llu\n", h_end_clock);
    printf("Elapsed cycles: %llu\n", (h_end_clock - h_start_clock));
    printf("Total GPU execution time: %.6f ms\n", elapsed_ms);

    // Cleanup
    free(h_out0);
    free(h_out1);

    for (int i = 0; i < numGPUs; i++) {
        CHECK_CUDA(cudaSetDevice(gpuIds[i]));
        CHECK_CUDA(cudaFree(d_outputs[i]));
    }

    CHECK_CUDA(cudaSetDevice(gpuIds[0]));
    CHECK_CUDA(cudaFree(d_ticketCounter));
    CHECK_CUDA(cudaFree(d_turn));
    CHECK_CUDA(cudaFree(d_sharedValue));
    CHECK_CUDA(cudaFree(d_chosenDeviceId));
    CHECK_CUDA(cudaFree(d_start_clock));
    CHECK_CUDA(cudaFree(d_end_clock));
    CHECK_CUDA(cudaFree(d_perGPUStartClocks));
    CHECK_CUDA(cudaFree(d_perDeviceCounts));

    return 0;
}
