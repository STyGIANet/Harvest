#include <stdio.h>
#include <stdlib.h>
#include <cuda_runtime.h>

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

	// Parity check
    	bool shouldEnter = false;
    	if (deviceId % 2 == 0 && currentVal % 2 == 0) {
        	shouldEnter = true;
    	} else if (deviceId % 2 != 0 && currentVal % 2 != 0) {
        	shouldEnter = true;
    	}
    	if (!shouldEnter) {
        	continue; // Skip this iteration and retry
    	}

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

    // On device 0: allocate shared memory
    cudaSetDevice(0);

    int *d_ticketCounter, *d_turn, *d_sharedValue, *d_chosenDeviceId;
    unsigned long long *d_start_clock, *d_end_clock, *d_perGPUStartClocks;

    cudaMalloc(&d_ticketCounter, sizeof(int));
    cudaMalloc(&d_turn, sizeof(int));
    cudaMalloc(&d_sharedValue, sizeof(int));
    cudaMalloc(&d_chosenDeviceId, sizeof(int));
    cudaMalloc(&d_start_clock, sizeof(unsigned long long));
    cudaMalloc(&d_end_clock, sizeof(unsigned long long));
    cudaMalloc(&d_perGPUStartClocks, deviceCount * sizeof(unsigned long long));

    int zero = 0, minusOne = -1;
    cudaMemcpy(d_ticketCounter, &zero, sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_turn, &zero, sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_sharedValue, &totalOperations, sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_chosenDeviceId, &minusOne, sizeof(int), cudaMemcpyHostToDevice);

    // Allocate output buffers on each device
    int **d_outputs = new int*[deviceCount];
    int *h_outputs = new int[totalOperations];

    for (int i = 0; i < deviceCount; i++) {
        cudaSetDevice(i);
        cudaMalloc(&d_outputs[i], opsPerDevice * sizeof(int));

        if (i != 0) {
            int canAccessPeer;
            cudaDeviceCanAccessPeer(&canAccessPeer, i, 0);
            if (canAccessPeer) {
                cudaDeviceEnablePeerAccess(0, 0);
            } else {
                printf("Warning: GPU %d cannot access peer GPU 0 memory\n", i);
                // If P2P not possible, program needs adjustment
            }
        }
    }

    // Launch kernels passing device 0's pointers to shared memory on all devices
    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        p2pKernel<<<1, 1>>>(
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
	cudaMemcpy(&h_outputs[i * opsPerDevice], d_outputs[i], opsPerDevice * sizeof(int), cudaMemcpyDeviceToHost);
        for (int t = 0; t < opsPerDevice; ++t) {
            printf("GPU %d, Thread %d got sharedValue = %d\n", i, t, h_outputs[i * opsPerDevice + t]);
        }
    }


    // Copy timing and chosenDeviceId info from device 0 to host
    int h_chosenDeviceId;
    unsigned long long h_start_clock, h_end_clock;

    cudaMemcpy(&h_chosenDeviceId, d_chosenDeviceId, sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(&h_start_clock, d_start_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost);
    cudaMemcpy(&h_end_clock, d_end_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost);

    // Print output
    for (int i = 0; i < totalOperations; ++i) {
        if (h_outputs[i] > 0) {
            printf("Operation %d result: %d\n", i, h_outputs[i]);
        }
    }

    int clockRateKHz = 0;
    cudaDeviceGetAttribute(&clockRateKHz, cudaDevAttrClockRate, h_chosenDeviceId);

    double elapsed_ms = (double)(h_end_clock - h_start_clock) / (clockRateKHz * 1000.0);
    printf("\n--- Timing Info ---\n");
    printf("Start clock64: %llu\n", h_start_clock);
    printf("End clock64:   %llu\n", h_end_clock);
    printf("Elapsed cycles: %llu\n", (h_end_clock - h_start_clock));
    printf("Total GPU execution time: %.6f ms\n", elapsed_ms);

    // Cleanup
    for (int i = 0; i < deviceCount; ++i) {
        cudaSetDevice(i);
        cudaFree(d_outputs[i]);
    }
    delete[] d_outputs;
    delete[] h_outputs;

    cudaSetDevice(0);
    cudaFree(d_ticketCounter);
    cudaFree(d_turn);
    cudaFree(d_sharedValue);
    cudaFree(d_chosenDeviceId);
    cudaFree(d_start_clock);
    cudaFree(d_end_clock);
    cudaFree(d_perGPUStartClocks);

    return 0;
}
