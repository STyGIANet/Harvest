// run_perm_step.cu
//
// One-step permutation microbenchmark.
// Each rank sends chunk_bytes to dst[rank] and receives chunk_bytes
// from the unique rank that maps to it.
//
// Example:
//   mpirun -np 8 ./run_perm_step 2 3 4 5 6 7 0 1 1048576

#include <mpi.h>
#include <nccl.h>
#include <cuda_runtime.h>

#include <cstdio>
#include <cstdlib>
#include <vector>

int main(int argc, char** argv) {
  MPI_Init(&argc, &argv);

  int rank, nranks;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Comm_size(MPI_COMM_WORLD, &nranks);

  if (argc != 1 + nranks + 1) {
    if (rank == 0) {
      printf("Usage:\n");
      printf("  mpirun -np <P> %s d0 d1 ... d(P-1) chunk_bytes\n", argv[0]);
    }
    MPI_Finalize();
    return 0;
  }

  // Parse destination map
  std::vector<int> dst_map(nranks);
  for (int i = 0; i < nranks; i++)
    dst_map[i] = atoi(argv[1 + i]);

  size_t chunk_bytes = (size_t)atoll(argv[1 + nranks]);

  int dst = dst_map[rank];

  // Find who sends to me
  int src = -1;
  for (int i = 0; i < nranks; i++) {
    if (dst_map[i] == rank) {
      src = i;
      break;
    }
  }

  cudaSetDevice(rank);

  // NCCL init
  ncclUniqueId id;
  if (rank == 0) ncclGetUniqueId(&id);
  MPI_Bcast(&id, sizeof(id), MPI_BYTE, 0, MPI_COMM_WORLD);

  ncclComm_t comm;
  ncclCommInitRank(&comm, nranks, id, rank);

  cudaStream_t stream;
  cudaStreamCreate(&stream);

  char* sendbuf;
  char* recvbuf;
  cudaMalloc(&sendbuf, chunk_bytes);
  cudaMalloc(&recvbuf, chunk_bytes);

  cudaMemset(sendbuf, rank, chunk_bytes);
  cudaMemset(recvbuf, 0, chunk_bytes);

  MPI_Barrier(MPI_COMM_WORLD);

  ncclGroupStart();
  ncclSend(sendbuf, chunk_bytes, ncclInt8, dst, comm, stream);
  ncclRecv(recvbuf, chunk_bytes, ncclInt8, src, comm, stream);
  ncclGroupEnd();

  cudaStreamSynchronize(stream);
  MPI_Barrier(MPI_COMM_WORLD);

  printf("[rank %d] sent %zu bytes to %d, received from %d\n",
         rank, chunk_bytes, dst, src);

  cudaFree(sendbuf);
  cudaFree(recvbuf);
  cudaStreamDestroy(stream);
  ncclCommDestroy(comm);

  MPI_Finalize();
  return 0;
}
