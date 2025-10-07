#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include <stdbool.h>
#include <time.h>
#define MAX_STRING_LEN (64*1024*1024) 

#define REPS 256

int msg(int rank, int size, int i) {
    int random;
    int msg_size;
    random = rand()%100;

    if(random < 50){
        msg_size = 16;
    }
    else if(random < 90){
        msg_size = 32;
    }
    else{
        msg_size = 64;
    }

    return msg_size * 1024 * 1024;
}
int main(int argc, char** argv){
    MPI_Init(&argc, &argv);

    int size, rank;
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    srand(time(NULL) + rank * 100);
    int msg_size;
    int random;
    char* dummy_send = malloc(MAX_STRING_LEN);
    char* dummy_recv = malloc(MAX_STRING_LEN);

    int left = (rank - 1 + size) % size;
    int right = (rank + 1) % size;


    printf("this is beggining and my left is: %d\n", left);

    for (int i = 0; i <8; i++) {
        int msg_size = msg(rank, size, i);
        if (msg_size > MAX_STRING_LEN) {
            printf("Error: msg_size exceeds buffer size!\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        for(int j = 0; j<msg_size; j++){
            dummy_send[j] = "abcdefghijklmnopqrstuvwxyz"[rand()%26];
        }

        if (rank % 2 == 0) {
            MPI_Send(dummy_send, msg_size, MPI_CHAR, right, 0, MPI_COMM_WORLD);
            MPI_Recv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, left, MPI_ANY_TAG, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        } else {
            MPI_Recv(dummy_recv, MAX_STRING_LEN, MPI_CHAR,left, MPI_ANY_TAG, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            MPI_Send(dummy_send, msg_size, MPI_CHAR, right, 0, MPI_COMM_WORLD);
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);

    double t0 = MPI_Wtime();
    for (int i = 0; i < REPS; i++) {
        int msg_size = msg(rank, size, i);
        if (msg_size > MAX_STRING_LEN) {
            printf("Error: msg_size exceeds buffer size!\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        for(int j = 0; j<msg_size; j++){
            dummy_send[j] = "abcdefghijklmnopqrstuvwxyz"[rand()%26];
        }

        if (rank % 2 == 0) {
            MPI_Send(dummy_send, msg_size, MPI_CHAR, right, 0, MPI_COMM_WORLD);
            MPI_Recv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, left, MPI_ANY_TAG, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        } else {
            MPI_Recv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, left, MPI_ANY_TAG, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            MPI_Send(dummy_send, msg_size, MPI_CHAR, right, 0, MPI_COMM_WORLD);
        }

        printf("IT: %d, rank: %d and my left is: %d\n", i, rank, left);

        printf("[rank %d] iter %d: received message\n", rank, i);
    }
    double t1 = MPI_Wtime();

    // report per-rank throughput (each rank transferred 2 * CHUNK * REPS bytes total)
    double bytes = 2.0 * (double)(32*1024*1024) * (double)REPS; // send + recv
    double gbps  = (bytes / (t1 - t0)) * 8.0 / 1e9;
    if (rank == 0) {
        printf("Ring: CHUNK=%zu bytes, REPS=%d, ranks=%d, time=%.3f s, per-rank throughput=%.1f Gb/s\n",
               32*1024*1024, REPS, size, (t1 - t0), gbps);
    }



    free(dummy_send);
    free(dummy_recv);

    MPI_Finalize();
    return 0;
}