#include <stdio.h>
#include <stdlib.h>
#include <cuda_runtime.h>

// Kernel: Each GPU runs this with 1 thread
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
    perGPUStartClocks[deviceId] = clock64();
    int counter = 0;

    while (true) {
        int currentVal = atomicAdd_system(sharedValue, 0);
        if (currentVal <= 0) break;

        // Acquire ticket
        int myTicket = atomicAdd_system(ticketCounter, 1);
        __threadfence_system();

        // Wait for turn
        while (atomicAdd_system(turn, 0) != myTicket) {
            __threadfence_system();
        }

        int newVal = -1;
        currentVal = atomicAdd_system(sharedValue, 0);
        if (currentVal > 0) {
            // Subtract 1 atomically across the system
            newVal = atomicAdd_system(sharedValue, -1);
            __threadfence_system();

            output[counter++] = newVal;

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

    int deviceCount;
    cudaGetDeviceCount(&deviceCount);

    if (deviceCount < 2) {
        printf("At least two GPUs are required.\n");
        return 1;
    }

    printf("Detected %d CUDA devices.\n", deviceCount);
    int opsPerDevice = totalOperations / deviceCount;
    printf("Running with %d total operations, %d per device.\n", totalOperations, opsPerDevice);

    // Shared memory - unified memory for system visibility
    int *ticketCounter, *turn, *sharedValue, *chosenDeviceId;
    unsigned long long *start_clock, *end_clock, *perGPUStartClocks;

    cudaMallocManaged(&ticketCounter, sizeof(int));
    cudaMallocManaged(&turn, sizeof(int));
    cudaMallocManaged(&sharedValue, sizeof(int));
    cudaMallocManaged(&chosenDeviceId, sizeof(int));
    cudaMallocManaged(&start_clock, sizeof(unsigned long long));
    cudaMallocManaged(&end_clock, sizeof(unsigned long long));
    cudaMallocManaged(&perGPUStartClocks, deviceCount * sizeof(unsigned long long));

    *ticketCounter = 0;
    *turn = 0;
    *sharedValue = totalOperations;
    *chosenDeviceId = -1;

    // Allocate per-GPU output buffers
    int **d_outputs = new int*[deviceCount];
    int *h_outputs = new int[totalOperations];

    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        cudaMallocManaged(&d_outputs[i], opsPerDevice * sizeof(int));
        for (int j = 0; j < opsPerDevice; ++j)
            d_outputs[i][j] = 0;

        if (i != 0) {
            int canAccessPeer;
            cudaDeviceCanAccessPeer(&canAccessPeer, i, 0);
            if (canAccessPeer) {
                cudaDeviceEnablePeerAccess(0, 0);
            }
        }
    }

    // Launch kernels
    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        p2pKernel<<<1, 1>>>(
            d_outputs[i],
            ticketCounter,
            turn,
            sharedValue,
            start_clock,
            end_clock,
            perGPUStartClocks,
            chosenDeviceId,
            i
        );
    }

    // Synchronize all devices
    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        cudaDeviceSynchronize();
    }

    // Collect and print output
    for (int i = 0; i < deviceCount; ++i) {
        for (int j = 0; j < opsPerDevice; ++j) {
            int val = d_outputs[i][j];
            h_outputs[i * opsPerDevice + j] = val;
            if (val > 0) {
                printf("GPU %d got sharedValue = %d\n", i, val);
            }
        }
    }

    // Timing info
    int clockRateKHz = 0;
    cudaDeviceGetAttribute(&clockRateKHz, cudaDevAttrClockRate, 0);

    double elapsed_ms = (*end_clock - *start_clock) / (clockRateKHz * 1000.0);
    printf("\n--- Timing Info ---\n");
    printf("Start clock64: %llu\n", *start_clock);
    printf("End clock64:   %llu\n", *end_clock);
    printf("Elapsed cycles: %llu\n", (*end_clock - *start_clock));
    printf("Total GPU execution time: %.6f ms\n", elapsed_ms);
    printf("Final sharedValue: %d\n", *sharedValue);
    printf("Chosen Device ID: %d\n", *chosenDeviceId);

    // Cleanup
    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        cudaFree(d_outputs[i]);
    }
    delete[] d_outputs;
    delete[] h_outputs;

    cudaFree(ticketCounter);
    cudaFree(turn);
    cudaFree(sharedValue);
    cudaFree(chosenDeviceId);
    cudaFree(start_clock);
    cudaFree(end_clock);
    cudaFree(perGPUStartClocks);

    return 0;
}
