#include <stdio.h>
#include <stdlib.h>
#include <cuda_runtime.h>

// Kernel: Each GPU runs totalOperations / deviceCount threads
__global__ void p2pKernel(
    int *output,
    int *ticketCounter,
    int *turn,
    int *sharedValue,
    unsigned long long *start_clock,
    unsigned long long *end_clock,
    unsigned long long *perGPUStartClocks,
    int *chosenDeviceId,
    int deviceId
) {
    int tid = threadIdx.x + blockIdx.x * blockDim.x;

    // Record per-GPU clock once
    if (tid == 0) {
        perGPUStartClocks[deviceId] = clock64();
    }
    __syncthreads();

    // Check sharedValue without modifying
    int currentVal = atomicAdd_system(sharedValue, 0);
    if (currentVal <= 0) return;

    // Acquire ticket
    int myTicket = atomicAdd_system(ticketCounter, 1);
    __threadfence_system();  // Make sure ticketCounter is visible

    // Wait until our ticket is served
    while (atomicAdd_system(turn, 0) != myTicket) {
        //__nanosleep(100);  // reduce contention
    }

    // Inside critical section
    currentVal = atomicAdd_system(sharedValue, 0);
    if (currentVal > 0) {
        int newVal = atomicAdd_system(sharedValue, -1);
        __threadfence_system();  // Make sure decrement is globally visible

        output[tid] = newVal;

        if (newVal == 1) {
            *chosenDeviceId = deviceId;
            *start_clock = perGPUStartClocks[deviceId];
            *end_clock = clock64();
        }
    }

    // Release lock
    atomicAdd_system(turn, 1);
    __threadfence_system();  // Ensure next thread sees updated turn
}

int main(int argc, char **argv) {
    if (argc != 2) {
        printf("Usage: %s <total_operations>\n", argv[0]);
        return 1;
    }

    int totalOperations = atoi(argv[1]);
    if (totalOperations <= 0) {
        printf("totalOperations must be > 0\n");
        return 1;
    }

    int deviceCount;
    cudaGetDeviceCount(&deviceCount);

    if (deviceCount < 2) {
        printf("At least two GPUs are required.\n");
        return 1;
    }

    printf("Running with %d GPUs and %d total operations.\n", deviceCount, totalOperations);

    int *d_ticketCounter, *d_turn, *d_sharedValue, *d_chosenDeviceId;
    unsigned long long *d_start_clock, *d_end_clock, *d_perGPUStartClocks;

    cudaSetDevice(0);
    cudaMalloc(&d_ticketCounter, sizeof(int));
    cudaMalloc(&d_turn, sizeof(int));
    cudaMalloc(&d_sharedValue, sizeof(int));
    cudaMalloc(&d_chosenDeviceId, sizeof(int));
    cudaMalloc(&d_start_clock, sizeof(unsigned long long));
    cudaMalloc(&d_end_clock, sizeof(unsigned long long));
    cudaMalloc(&d_perGPUStartClocks, deviceCount * sizeof(unsigned long long));

    cudaMemset(d_ticketCounter, 0, sizeof(int));
    cudaMemset(d_turn, 0, sizeof(int));
    cudaMemset(d_chosenDeviceId, -1, sizeof(int));
    cudaMemcpy(d_sharedValue, &totalOperations, sizeof(int), cudaMemcpyHostToDevice);

    // Output buffers
    int **d_outputs = new int*[deviceCount];
    int *h_outputs = new int[totalOperations];
    int opsPerGPU = totalOperations / deviceCount;

    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        cudaMalloc(&d_outputs[i], opsPerGPU * sizeof(int));
        cudaMemset(d_outputs[i], -1, opsPerGPU * sizeof(int));

        if (i != 0) {
            int canAccessPeer = 0;
            cudaDeviceCanAccessPeer(&canAccessPeer, i, 0);
            if (canAccessPeer) {
                cudaDeviceEnablePeerAccess(0, 0);
            }
        }
    }

    // Launch kernel on each GPU
    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        p2pKernel<<<1, opsPerGPU>>>(
            d_outputs[i],
            d_ticketCounter,
            d_turn,
            d_sharedValue,
            d_start_clock,
            d_end_clock,
            d_perGPUStartClocks,
            d_chosenDeviceId,
            i
        );
    }

    // Synchronize all devices
    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        cudaDeviceSynchronize();
    }

    // Print output
    for (int i = 0; i < deviceCount; ++i) {
        cudaMemcpy(&h_outputs[i * opsPerGPU], d_outputs[i], opsPerGPU * sizeof(int), cudaMemcpyDeviceToHost);
        for (int j = 0; j < opsPerGPU; ++j) {
            int val = h_outputs[i * opsPerGPU + j];
            if (val > 0) {
                printf("GPU %d, Thread %d got sharedValue = %d\n", i, j, val);
            }
        }
    }

    // Timing
    unsigned long long h_start_clock = 0, h_end_clock = 0;
    int h_chosenDeviceId = -1;
    cudaMemcpy(&h_start_clock, d_start_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost);
    cudaMemcpy(&h_end_clock, d_end_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost);
    cudaMemcpy(&h_chosenDeviceId, d_chosenDeviceId, sizeof(int), cudaMemcpyDeviceToHost);

    int clockRateKHz = 0;
    cudaDeviceGetAttribute(&clockRateKHz, cudaDevAttrClockRate, h_chosenDeviceId);
    double timeMs = (h_end_clock - h_start_clock) / (clockRateKHz * 1000.0);

    printf("\n--- Timing Info ---\n");
    printf("Start clock64: %llu\n", h_start_clock);
    printf("End clock64:   %llu\n", h_end_clock);
    printf("Elapsed cycles: %llu\n", (h_end_clock - h_start_clock));
    printf("Total GPU execution time: %.6f ms\n", timeMs);

    int finalSharedValue = -1;
    cudaMemcpy(&finalSharedValue, d_sharedValue, sizeof(int), cudaMemcpyDeviceToHost);
    printf("Final sharedValue: %d\n", finalSharedValue);

    // Cleanup
    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        cudaFree(d_outputs[i]);
    }

    delete[] d_outputs;
    delete[] h_outputs;

    cudaFree(d_ticketCounter);
    cudaFree(d_turn);
    cudaFree(d_sharedValue);
    cudaFree(d_chosenDeviceId);
    cudaFree(d_start_clock);
    cudaFree(d_end_clock);
    cudaFree(d_perGPUStartClocks);

    return 0;
}
