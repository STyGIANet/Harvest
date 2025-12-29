#include <stdio.h>
#include <stdlib.h>
#include <cuda.h>
#include <nvshmem.h>
#include <nvshmemx.h>

// Kernel
__global__ void p2pKernel_nvshmem(
    int *output,
    int *ticketCounter,
    int *turn,
    int *sharedValue,
    unsigned long long *start_clock,
    unsigned long long *end_clock,
    unsigned long long *perGPUStartClocks,
    int *chosenDeviceId,
    int my_pe
) {
    if (threadIdx.x == 0) {
        perGPUStartClocks[my_pe] = clock64();
    }
    __syncthreads();

    // Take ticket using NVSHMEM atomic add
    int myTicket = nvshmem_int_atomic_fetch_add(ticketCounter, 1, 0);

    while (nvshmem_int_atomic_fetch(turn, 0) != myTicket) {
        // Busy wait
    }

    // Critical Section
    int newVal = nvshmem_int_atomic_fetch_add(sharedValue, -1, 0);
    output[threadIdx.x] = newVal;

    if (newVal == 1) {
        // Chosen GPU sets the result (only one will set)
        nvshmem_int_p(chosenDeviceId, my_pe, 0);
    }

    // Release lock
    nvshmem_int_atomic_add(turn, 1, 0);

    __syncthreads();

    if (threadIdx.x == 0) {
        if (nvshmem_int_g(chosenDeviceId, 0) == my_pe) {
            *start_clock = perGPUStartClocks[my_pe];
            *end_clock = clock64();
        }
    }
}

int main(int argc, char **argv) {
    nvshmem_init();
    int num_pes = nvshmem_n_pes();
    int my_pe = nvshmem_my_pe();

    int T = 4;
    if (argc >= 2) {
        T = atoi(argv[1]);
        if (T <= 0 || T > 1024) {
            if (my_pe == 0) printf("Invalid thread count. Must be 1–1024.\n");
            nvshmem_finalize();
            return 1;
        }
    }

    if (my_pe == 0) {
        printf("Detected %d GPUs (PEs)\n", num_pes);
        printf("Running with %d threads per GPU.\n", T);
    }

    // Symmetric allocations
    int *ticketCounter = (int*) nvshmem_malloc(sizeof(int));
    int *turn = (int*) nvshmem_malloc(sizeof(int));
    int *sharedValue = (int*) nvshmem_malloc(sizeof(int));
    int *chosenDeviceId = (int*) nvshmem_malloc(sizeof(int));
    unsigned long long *start_clock = (unsigned long long*) nvshmem_malloc(sizeof(unsigned long long));
    unsigned long long *end_clock = (unsigned long long*) nvshmem_malloc(sizeof(unsigned long long));
    unsigned long long *perGPUStartClocks = (unsigned long long*) nvshmem_malloc(num_pes * sizeof(unsigned long long));

    int *output;
    cudaMalloc(&output, T * sizeof(int));

    // Initialization only on PE 0
    if (my_pe == 0) {
        *ticketCounter = 0;
        *turn = 0;
        *chosenDeviceId = -1;
        int totalOps = num_pes * T;
        *sharedValue = totalOps;
    }

    nvshmem_barrier_all();  // Make sure everyone sees initialized values

    // Launch kernel
    p2pKernel_nvshmem<<<1, T>>>(
        output,
        ticketCounter,
        turn,
        sharedValue,
        start_clock,
        end_clock,
        perGPUStartClocks,
        chosenDeviceId,
        my_pe
    );

    cudaDeviceSynchronize();

    // Output
    int *h_output = new int[T];
    cudaMemcpy(h_output, output, T * sizeof(int), cudaMemcpyDeviceToHost);
    for (int i = 0; i < T; ++i) {
        printf("PE %d, Thread %d got sharedValue = %d\n", my_pe, i, h_output[i]);
    }

    // Timing output
    nvshmem_barrier_all();
    if (my_pe == 0) {
        unsigned long long h_start, h_end;
        int h_chosen;
        cudaMemcpy(&h_start, start_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost);
        cudaMemcpy(&h_end, end_clock, sizeof(unsigned long long), cudaMemcpyDeviceToHost);
        cudaMemcpy(&h_chosen, chosenDeviceId, sizeof(int), cudaMemcpyDeviceToHost);

        int clockRateKHz;
        cudaDeviceGetAttribute(&clockRateKHz, cudaDevAttrClockRate, h_chosen);
        unsigned long long elapsed_cycles = h_end - h_start;
        double time_ms = elapsed_cycles / (clockRateKHz * 1000.0);

        printf("\n--- Timing Info ---\n");
        printf("Start clock64: %llu\n", h_start);
        printf("End clock64:   %llu\n", h_end);
        printf("Elapsed cycles: %llu\n", elapsed_cycles);
        printf("Total GPU execution time: %.6f ms\n", time_ms);
    }

    delete[] h_output;
    cudaFree(output);

    nvshmem_free(ticketCounter);
    nvshmem_free(turn);
    nvshmem_free(sharedValue);
    nvshmem_free(start_clock);
    nvshmem_free(end_clock);
    nvshmem_free(perGPUStartClocks);
    nvshmem_free(chosenDeviceId);

    nvshmem_finalize();
    return 0;
}

