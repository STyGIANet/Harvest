// three_gpu_shared_state.cu
//
// GPUs 0 and 1 do the work.
// GPU 2 holds ONLY the shared state: sharedValue, ticketCounter, turn, counts, timing, etc.
//
// Build:
//   nvcc -O3 -arch=sm_70 -lineinfo three_gpu_shared_state.cu -o three_gpu_shared_state
//
// Run:
//   ./three_gpu_shared_state 32
//
// Notes / requirements:
// - You need >= 3 GPUs.
// - GPU0->GPU2 and GPU1->GPU2 must support P2P (peer access).
// - This uses *_system atomics and __threadfence_system() with Unified Virtual Addressing + P2P.

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

static void printP2PAttrs(int fromDev, int toDev) {
    int access = 0, atomics = 0, perfRank = 0;
    CHECK_CUDA(cudaDeviceGetP2PAttribute(&access, cudaDevP2PAttrAccessSupported, fromDev, toDev));
    CHECK_CUDA(cudaDeviceGetP2PAttribute(&atomics, cudaDevP2PAttrNativeAtomicSupported, fromDev, toDev));
    CHECK_CUDA(cudaDeviceGetP2PAttribute(&perfRank, cudaDevP2PAttrPerformanceRank, fromDev, toDev));

    printf("P2P %d -> %d: access=%d nativeAtomics=%d perfRank=%d\n",
           fromDev, toDev, access, atomics, perfRank);
}

__global__ void p2pKernel(
    int *output,
    int *ticketCounter,
    int *turn,
    int *sharedValue,
    unsigned long long *start_clock,
    unsigned long long *end_clock,
    unsigned long long *perGPUStartClocks,
    int *chosenDeviceId,
    int *perDeviceCounts,     // counts array sized = numWorkers
    int maxOutPerDevice,
    int deviceId              // logical worker id: 0 or 1
) {
    // Record a start clock once per worker GPU
    if (threadIdx.x == 0) {
        perGPUStartClocks[deviceId] = clock64();
        __threadfence_system();
    }

    while (true) {
        int currentVal = atomicAdd_system(sharedValue, 0);
        if (currentVal <= 0) break;

        // Parity gating (kept from your code)
        bool shouldEnter = false;
        if ((deviceId % 2 == 0) && (currentVal % 2 == 0)) shouldEnter = true;
        else if ((deviceId % 2 != 0) && (currentVal % 2 != 0)) shouldEnter = true;
        if (!shouldEnter) continue;

        int myTicket = atomicAdd_system(ticketCounter, 1);
        __threadfence_system();

        while (atomicAdd_system(turn, 0) != myTicket) {
            __nanosleep(10);
            __threadfence_system();
        }

        int newVal = -1;
        currentVal = atomicAdd_system(sharedValue, 0);
        if (currentVal > 0) {
            newVal = atomicAdd_system(sharedValue, -1);
            __threadfence_system();

            int outIdx = atomicAdd_system(&perDeviceCounts[deviceId], 1);
            if (outIdx < maxOutPerDevice) {
                output[outIdx] = newVal;
            }
            else{
                atomicAdd_system(&perDeviceCounts[deviceId], -1);
            }

            if (newVal == 1) {
                *chosenDeviceId = deviceId;               // logical worker id
                *start_clock = perGPUStartClocks[deviceId];
                *end_clock   = clock64();
                __threadfence_system();
            }
        }

        atomicAdd_system(turn, 1);
        __threadfence_system();
    }
}

static void requirePeerAccess(int fromDev, int toDev, const char* what) {
    int can = 0;
    CHECK_CUDA(cudaDeviceCanAccessPeer(&can, fromDev, toDev));
    if (!can) {
        fprintf(stderr,
                "ERROR: P2P not available for %s: GPU %d -> GPU %d\n",
                what, fromDev, toDev);
        exit(1);
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
    if (deviceCount < 3) {
        printf("Need at least 3 GPUs (2 workers + 1 state GPU). Detected %d.\n", deviceCount);
        return 1;
    }

    printP2PAttrs(1, 0);
    printP2PAttrs(2, 0);


    // Two worker GPUs + one dedicated "state" GPU
    const int numWorkers = 2;
    int workerGpuIds[numWorkers] = {0, 1};
    int stateGpuId = 3;

    printf("Detected %d CUDA devices.\n", deviceCount);
    printf("Workers: GPU %d and GPU %d\n", workerGpuIds[0], workerGpuIds[1]);
    printf("State  : GPU %d (holds sharedVariable/ticket/turn/etc.)\n", stateGpuId);

    int blocksPerGPU  = 1;
    int threadsPerGPU = 1;

    int maxOutPerDevice = totalOperations / numWorkers;

    printf("Running with %d total operations.\n", totalOperations);
    printf("Launch config per worker GPU: blocks=%d, threads=%d\n", blocksPerGPU, threadsPerGPU);
    printf("Output capacity per worker GPU: %d\n", maxOutPerDevice);

    // ----------------------------
    // Allocate ALL shared state on the dedicated state GPU
    // ----------------------------
    CHECK_CUDA(cudaSetDevice(stateGpuId));

    int *d_ticketCounter = nullptr, *d_turn = nullptr, *d_sharedValue = nullptr;
    int *d_chosenDeviceId = nullptr, *d_perDeviceCounts = nullptr;
    unsigned long long *d_start_clock = nullptr, *d_end_clock = nullptr, *d_perGPUStartClocks = nullptr;

    CHECK_CUDA(cudaMalloc(&d_ticketCounter, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_turn, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_sharedValue, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_chosenDeviceId, sizeof(int)));
    CHECK_CUDA(cudaMalloc(&d_start_clock, sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_end_clock, sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_perGPUStartClocks, numWorkers * sizeof(unsigned long long)));
    CHECK_CUDA(cudaMalloc(&d_perDeviceCounts, numWorkers * sizeof(int)));

    int zero = 0, minusOne = -1;
    CHECK_CUDA(cudaMemcpy(d_ticketCounter, &zero, sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(d_turn, &zero, sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(d_sharedValue, &totalOperations, sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(d_chosenDeviceId, &minusOne, sizeof(int), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemset(d_perGPUStartClocks, 0, numWorkers * sizeof(unsigned long long)));
    CHECK_CUDA(cudaMemset(d_perDeviceCounts, 0, numWorkers * sizeof(int)));
    CHECK_CUDA(cudaMemset(d_start_clock, 0, sizeof(unsigned long long)));
    CHECK_CUDA(cudaMemset(d_end_clock, 0, sizeof(unsigned long long)));

    // ----------------------------
    // Enable peer access: each worker must be able to access state GPU allocations
    // ----------------------------
    for (int i = 0; i < numWorkers; i++) {
        int w = workerGpuIds[i];

        requirePeerAccess(w, stateGpuId, "worker->state shared state access");

        CHECK_CUDA(cudaSetDevice(w));
        // Enable access to state GPU
        CHECK_CUDA(cudaDeviceEnablePeerAccess(stateGpuId, 0));
    }

    // (Optional) If you ever wanted state GPU to directly read worker output buffers,
    // you’d also enable stateGpuId -> worker. Not needed for this program.

    // ----------------------------
    // Allocate per-worker output buffers on their OWN GPUs (local)
    // ----------------------------
    int *d_outputs[numWorkers] = {nullptr, nullptr};

    for (int i = 0; i < numWorkers; i++) {
        CHECK_CUDA(cudaSetDevice(workerGpuIds[i]));
        CHECK_CUDA(cudaMalloc(&d_outputs[i], maxOutPerDevice * sizeof(int)));
        CHECK_CUDA(cudaMemset(d_outputs[i], 0, maxOutPerDevice * sizeof(int)));
    }

    // ----------------------------
    // Launch on each worker, but pass pointers that live on STATE GPU
    // ----------------------------
    for (int i = 0; i < numWorkers; i++) {
        CHECK_CUDA(cudaSetDevice(workerGpuIds[i]));
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
            /*deviceId=*/i   // logical worker id: 0 or 1
        );
        CHECK_CUDA(cudaGetLastError());
    }

    // Sync workers
    for (int i = 0; i < numWorkers; i++) {
        CHECK_CUDA(cudaSetDevice(workerGpuIds[i]));
        CHECK_CUDA(cudaDeviceSynchronize());
    }

    // ----------------------------
    // Read results from STATE GPU and outputs from WORKER GPUs
    // ----------------------------
    int h_counts[numWorkers] = {0, 0};
    int h_chosenDeviceId = -1;
    unsigned long long h_start_clock = 0, h_end_clock = 0;

    CHECK_CUDA(cudaSetDevice(stateGpuId));
    CHECK_CUDA(cudaMemcpy(h_counts, d_perDeviceCounts, numWorkers * sizeof(int), cudaMemcpyDeviceToHost));
    CHECK_CUDA(cudaMemcpy(&h_chosenDeviceId, d_chosenDeviceId, sizeof(int), cudaMemcpyDeviceToHost));
    CHECK_CUDA(cudaMemcpy(&h_start_clock, d_start_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost));
    CHECK_CUDA(cudaMemcpy(&h_end_clock, d_end_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost));

    int *h_out[numWorkers] = {nullptr, nullptr};
    for (int i = 0; i < numWorkers; i++) {
        h_out[i] = (int*)malloc((size_t)h_counts[i] * sizeof(int));
        CHECK_CUDA(cudaSetDevice(workerGpuIds[i]));
        if (h_counts[i] > 0) {
            CHECK_CUDA(cudaMemcpy(h_out[i], d_outputs[i], (size_t)h_counts[i] * sizeof(int),
                                  cudaMemcpyDeviceToHost));
        }
    }

    for (int i = 0; i < numWorkers; i++) {
        for (int t = 0; t < h_counts[i]; t++) {
            printf("Worker GPU logical %d (cuda %d) wrote[%d] = %d\n",
                   i, workerGpuIds[i], t, h_out[i][t]);
        }
    }

    // ----------------------------
    // Timing conversion: use the CHOSEN worker GPU's clock rate
    // ----------------------------
    double elapsed_ms = 0.0;
    if (h_chosenDeviceId >= 0 && h_chosenDeviceId < numWorkers && h_end_clock >= h_start_clock) {
        int chosenCudaDev = workerGpuIds[h_chosenDeviceId];
        int clockRateKHz = 0;
        CHECK_CUDA(cudaDeviceGetAttribute(&clockRateKHz, cudaDevAttrClockRate, chosenCudaDev));
        elapsed_ms = (double)(h_end_clock - h_start_clock) / (clockRateKHz * 1000.0);
    }

    printf("\n--- Timing Info ---\n");
    printf("Chosen worker (logical id): %d\n", h_chosenDeviceId);
    printf("Start clock64: %llu\n", h_start_clock);
    printf("End clock64:   %llu\n", h_end_clock);
    printf("Elapsed cycles: %llu\n", (h_end_clock - h_start_clock));
    printf("Total GPU execution time: %.6f ms\n", elapsed_ms);

    // ----------------------------
    // Cleanup
    // ----------------------------
    for (int i = 0; i < numWorkers; i++) {
        free(h_out[i]);
        CHECK_CUDA(cudaSetDevice(workerGpuIds[i]));
        CHECK_CUDA(cudaFree(d_outputs[i]));
    }

    CHECK_CUDA(cudaSetDevice(stateGpuId));
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
