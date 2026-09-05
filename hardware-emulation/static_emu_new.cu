#include <mpi.h>
#include <nccl.h>
#include <cuda_runtime.h>

#include <cstdio>
#include <cstdlib>
#include <vector>
#include <string>
#include <algorithm>


static inline void die_mpi(int e, int rank) {
    if (e != MPI_SUCCESS) {
        char s[MPI_MAX_ERROR_STRING]; int n = 0;
        MPI_Error_string(e, s, &n);
        fprintf(stderr, "[%d] MPI: %.*s\n", rank, n, s);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

static inline void die_cuda(cudaError_t e, int rank) {
    if (e != cudaSuccess) {
        fprintf(stderr, "[%d] CUDA: %s\n", rank, cudaGetErrorString(e));
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

static inline void die_nccl(ncclResult_t r, int rank) {
    if (r != ncclSuccess) {
        fprintf(stderr, "[%d] NCCL: %s\n", rank, ncclGetErrorString(r));
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

static inline int get_int_env(const char* name, int defv) {
    const char* s = std::getenv(name);
    return s ? std::atoi(s) : defv;
}

int main(int argc, char** argv) {
    die_mpi(MPI_Init(&argc, &argv), 0);

    int rank = 0, nranks = 0;
    die_mpi(MPI_Comm_rank(MPI_COMM_WORLD, &rank), rank);
    die_mpi(MPI_Comm_size(MPI_COMM_WORLD, &nranks), rank);

    if (argc < 1 + nranks + 1) {
        if (rank == 0) {
            fprintf(stderr,
                    "Usage: %s d0..d(P-1) chunk_bytes [warmup] [iters]\n", argv[0]);
        }
        MPI_Finalize();
        return 1;
    }

    std::vector<int> dst_map(nranks);
    for (int i = 0; i < nranks; i++) dst_map[i] = std::atoi(argv[1 + i]);
    size_t chunk_bytes = (size_t)std::atoll(argv[1 + nranks]);

    int warmup = 20, iters = 10;
    int argp = 1 + nranks + 1;
    if (argc > argp) warmup = std::atoi(argv[argp++]);
    if (argc > argp) iters  = std::atoi(argv[argp++]);

    if (chunk_bytes > (size_t)INT_MAX) {
        if (rank == 0) fprintf(stderr, "chunk_bytes=%zu too large (must be <= INT_MAX for ncclInt8 count)\n", chunk_bytes);
        MPI_Abort(MPI_COMM_WORLD, 4);
    }
    int count = (int)chunk_bytes;

    int dst = dst_map[rank];
    int src = -1;
    for (int i = 0; i < nranks; i++) {
        if (dst_map[i] == rank) { src = i; break; }
    }
    if (dst < 0 || dst >= nranks || src < 0) {
        if (rank == 0) fprintf(stderr, "Destination map must be a permutation of [0..P-1]\n");
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    if (dst == rank || src == rank) {
        if (rank == 0) fprintf(stderr, "Invalid permutation: self-send/recv detected (rank maps to itself)\n");
        MPI_Abort(MPI_COMM_WORLD, 5);
    }

    // std::string perm_str;
    // if (rank == 0) {
    //     for (int i = 0; i < nranks; i++) {
    //         perm_str += std::to_string(dst_map[i]);
    //         if (i != nranks - 1) perm_str += "-";
    //     }
    // }

    int devs = 0;
    die_cuda(cudaGetDeviceCount(&devs), rank);
    if (devs <= 0) MPI_Abort(MPI_COMM_WORLD, 3);

    // Prefer local-rank if present; fallback to rank%devs
    int local_rank = get_int_env("OMPI_COMM_WORLD_LOCAL_RANK", -1);
    if (local_rank < 0) local_rank = get_int_env("SLURM_LOCALID", -1);
    int dev = (local_rank >= 0) ? (local_rank % devs) : (rank % devs);

    die_cuda(cudaSetDevice(dev), rank);

    // cudaDeviceProp prop;
    // die_cuda(cudaGetDeviceProperties(&prop, dev), rank);
    // printf("[rank %d] using CUDA device %d  PCI %04x:%02x:%02x.0  src=%d dst=%d\n",
    //        rank, dev, prop.pciDomainID, prop.pciBusID, prop.pciDeviceID, src, dst);
    // fflush(stdout);

    cudaStream_t stream;
    die_cuda(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), rank);

    char *sendbuf = nullptr, *recvbuf = nullptr;
    die_cuda(cudaMalloc(&sendbuf, chunk_bytes), rank);
    die_cuda(cudaMalloc(&recvbuf, chunk_bytes), rank);
    die_cuda(cudaMemset(sendbuf, 1, chunk_bytes), rank);
    die_cuda(cudaMemset(recvbuf, 0, chunk_bytes), rank);

    ncclUniqueId id{};
    if (rank == 0) die_nccl(ncclGetUniqueId(&id), rank);
    die_mpi(MPI_Bcast(&id, (int)sizeof(id), MPI_BYTE, 0, MPI_COMM_WORLD), rank);

    ncclComm_t comm;
    die_nccl(ncclCommInitRank(&comm, nranks, id, rank), rank);

    die_mpi(MPI_Barrier(MPI_COMM_WORLD), rank);
    die_cuda(cudaDeviceSynchronize(), rank);

    for (int i = 0; i < warmup; i++) {
        die_mpi(MPI_Barrier(MPI_COMM_WORLD), rank);

        die_nccl(ncclGroupStart(), rank);
        die_nccl(ncclSend(sendbuf, count, ncclInt8, dst, comm, stream), rank);
        die_nccl(ncclRecv(recvbuf, count, ncclInt8, src, comm, stream), rank);
        die_nccl(ncclGroupEnd(), rank);

        die_cuda(cudaStreamSynchronize(stream), rank);
    }

    std::vector<double> times;
    times.reserve(iters);

    die_mpi(MPI_Barrier(MPI_COMM_WORLD), rank);

    int batch = 1000;  // tune this (20–100 good range)

    std::vector<double> full_times, enqueue_times, wait_times;
    full_times.reserve(iters);

    for (int i = 0; i < iters; i += batch) {

        struct timespec ts;
        ts.tv_sec = 0;
        ts.tv_nsec = 10000 * 1000;
        nanosleep(&ts, nullptr);

        int b = std::min(batch, iters - i);

        double t0 = MPI_Wtime();

        // enqueue b operations
        for (int k = 0; k < b; k++) {
            die_nccl(ncclGroupStart(), rank);
            die_nccl(ncclSend(sendbuf, count, ncclInt8, dst, comm, stream), rank);
            die_nccl(ncclRecv(recvbuf, count, ncclInt8, src, comm, stream), rank);
            die_nccl(ncclGroupEnd(), rank);
        }

        double t1 = MPI_Wtime();

        die_cuda(cudaStreamSynchronize(stream), rank);

        double t2 = MPI_Wtime();
        die_mpi(MPI_Barrier(MPI_COMM_WORLD), rank);

        // amortized per-op time
        double local_full_ms    = ((t2 - t0) * 1000.0) / b;
        double local_enqueue_ms = ((t1 - t0) * 1000.0) / b;
        double local_wait_ms    = ((t2 - t1) * 1000.0) / b;

        double full_ms = 0.0, enqueue_ms = 0.0, wait_ms = 0.0;

        die_mpi(MPI_Reduce(&local_full_ms,    &full_ms,    1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD), rank);
        die_mpi(MPI_Reduce(&local_enqueue_ms, &enqueue_ms, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD), rank);
        die_mpi(MPI_Reduce(&local_wait_ms,    &wait_ms,    1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD), rank);

        if (rank == 0) {
            full_times.push_back(full_ms);
            enqueue_times.push_back(enqueue_ms);
            wait_times.push_back(wait_ms);
        }
    }

    // if (rank == 0) {
    //     std::sort(full_times.begin(), full_times.end());
    //     std::sort(enqueue_times.begin(), enqueue_times.end());
    //     std::sort(wait_times.begin(), wait_times.end());

    //     double full_med    = full_times[full_times.size()/2];
    //     double enqueue_med = enqueue_times[enqueue_times.size()/2];
    //     double wait_med    = wait_times[wait_times.size()/2];

    //     printf("%zu, full=%.6f ms, enqueue=%.6f ms, wait=%.6f ms\n",
    //            chunk_bytes, full_med, enqueue_med, wait_med);
    //     fflush(stdout);
    // }


    if (rank == 0) {
        std::sort(full_times.begin(), full_times.end());
        std::sort(enqueue_times.begin(), enqueue_times.end());
        std::sort(wait_times.begin(), wait_times.end());

        double full_med    = full_times[0];
        double enqueue_med = enqueue_times[0];
        double wait_med    = wait_times[0];

        printf("%zu,%.6f,%.6f,%.6f\n",
               chunk_bytes, full_med, enqueue_med, wait_med);
        fflush(stdout);
    }


    // if (rank == 0) {
    //     std::sort(full_times.begin(), full_times.end());
    //     std::sort(enqueue_times.begin(), enqueue_times.end());
    //     std::sort(wait_times.begin(), wait_times.end());

    //     double full_sum = 0.0;
    //     double enqueue_sum = 0.0;
    //     double wait_sum = 0.0;

    //     for (size_t i = 0; i < full_times.size(); i++) {
    //         full_sum += full_times[i];
    //         enqueue_sum += enqueue_times[i];
    //         wait_sum += wait_times[i];
    //     }

    //     double full_avg    = full_sum / full_times.size();
    //     double enqueue_avg = enqueue_sum / enqueue_times.size();
    //     double wait_avg    = wait_sum / wait_times.size();


    //     printf("%zu,%.6f,%.6f,%.6f\n",
    //            chunk_bytes, full_avg, enqueue_avg, wait_avg);
    //     fflush(stdout);
    // }



    die_cuda(cudaFree(sendbuf), rank);
    die_cuda(cudaFree(recvbuf), rank);
    die_cuda(cudaStreamDestroy(stream), rank);
    die_nccl(ncclCommDestroy(comm), rank);

    MPI_Finalize();
    return 0;
}
