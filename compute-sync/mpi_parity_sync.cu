/* nvcc -O3 -std=c++17 \
     -ccbin mpicxx \
     mpi_parity_sync.cu \
     -o mpi_parity_sync
*/

#include <mpi.h>
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CHECK_CUDA(call)                                                     \
  do {                                                                       \
    cudaError_t _e = (call);                                                 \
    if (_e != cudaSuccess) {                                                 \
      fprintf(stderr, "CUDA error %s:%d: %s\n", __FILE__, __LINE__,          \
              cudaGetErrorString(_e));                                       \
      MPI_Abort(MPI_COMM_WORLD, 1);                                          \
    }                                                                        \
  } while (0)

// Dummy kernel to represent "work"
__global__ void do_work(int token, int *out, int idx) {
    if (threadIdx.x == 0)
        out[idx] = token;
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    int rank, world;
    double t_start = 0.0;
    double t_end = 0.0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &world);

    if (world != 3) {
        if (rank == 0)
            fprintf(stderr, "This program requires exactly 3 MPI ranks.\n");
        MPI_Finalize();
        return 1;
    }

    if (argc != 2) {
        if (rank == 0)
            fprintf(stderr, "Usage: %s <total_operations>\n", argv[0]);
        MPI_Finalize();
        return 1;
    }

    int totalOps = atoi(argv[1]);
    if (totalOps <= 0) {
        if (rank == 0)
            fprintf(stderr, "total_operations must be > 0\n");
        MPI_Finalize();
        return 1;
    }

    // One GPU per rank
    CHECK_CUDA(cudaSetDevice(rank));

    constexpr int STATE_RANK = 0;
    constexpr int ODD_WORKER = 1;
    constexpr int EVEN_WORKER = 2;

    // Output buffers on workers
    std::vector<int> local_out;
    int *d_out = nullptr;
    int local_count = 0;

    if (rank != STATE_RANK) {
        local_out.resize((totalOps + 1) / 2);
        CHECK_CUDA(cudaMalloc(&d_out, local_out.size() * sizeof(int)));
    }

    MPI_Barrier(MPI_COMM_WORLD);

    // -------------------------
    // STATE RANK (sharedValue)
    // -------------------------
    if (rank == STATE_RANK) {
        t_start = MPI_Wtime();
        for (int token = totalOps; token >= 1; --token) {
            int dest = (token % 2 == 0) ? EVEN_WORKER : ODD_WORKER;

            // Send token
            MPI_Send(&token, 1, MPI_INT, dest, 0, MPI_COMM_WORLD);

            // Wait for acknowledgment
            int ack;
            MPI_Recv(&ack, 1, MPI_INT, dest, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        }

        t_end = MPI_Wtime();

        // Termination signal
        int stop = -1;
        MPI_Send(&stop, 1, MPI_INT, ODD_WORKER, 0, MPI_COMM_WORLD);
        MPI_Send(&stop, 1, MPI_INT, EVEN_WORKER, 0, MPI_COMM_WORLD);
    }

    // -------------------------
    // WORKERS
    // -------------------------
    else {
        while (true) {
            int token;
            MPI_Recv(&token, 1, MPI_INT, STATE_RANK, 0, MPI_COMM_WORLD,
                     MPI_STATUS_IGNORE);

            if (token < 0)
                break;

            // Parity safety check
            if ((rank == ODD_WORKER && token % 2 == 0) ||
                (rank == EVEN_WORKER && token % 2 != 0)) {
                fprintf(stderr, "Parity violation on rank %d\n", rank);
                MPI_Abort(MPI_COMM_WORLD, 1);
            }

            // GPU "work"
            do_work<<<1, 1>>>(token, d_out, local_count);
            CHECK_CUDA(cudaDeviceSynchronize());

            local_count++;

            // Ack back to state
            MPI_Send(&token, 1, MPI_INT, STATE_RANK, 1, MPI_COMM_WORLD);
        }

        CHECK_CUDA(cudaMemcpy(local_out.data(), d_out,
                              local_count * sizeof(int),
                              cudaMemcpyDeviceToHost));

        for (int i = 0; i < local_count; i++) {
            printf("Worker rank %d wrote[%d] = %d\n",
                   rank, i, local_out[i]);
        }
    }

    if (rank != STATE_RANK)
        CHECK_CUDA(cudaFree(d_out));

    if (rank == STATE_RANK) {
        double elapsed_ms = (t_end - t_start) * 1000.0;

        printf("\n--- Timing Info ---\n");
        printf("State rank (arbiter): %d\n", STATE_RANK);
        printf("Start time (MPI_Wtime): %.9f s\n", t_start);
        printf("End time   (MPI_Wtime): %.9f s\n", t_end);
        printf("Elapsed time: %.6f ms\n", elapsed_ms);
    }


    MPI_Finalize();
    return 0;
}
