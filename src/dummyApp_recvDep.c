#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include <stdbool.h>
#include <time.h>

#define MAX_STRING_LEN 5000
#define NUM_MSGS 100

int main(int argc, char** argv){
    MPI_Init(&argc, &argv);

    int size, rank;
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    if (size != 4) {
        if (rank == 0)
            printf("This program needs exactly 4 processes.\n");
        MPI_Finalize();
        return 1;
    }

    int targets[3];

    switch(rank){
        case 0:
            targets[0] = 1;
            targets[1] = 2;
            targets[2] = 3;
            break;
        case 1:
            targets[0] = 2;
            targets[1] = 3;
            targets[2] = 0;
            break;
        case 2:
            targets[0] = 3;
            targets[1] = 0;
            targets[2] = 1;
            break;
        case 3:
            targets[0] = 0;
            targets[1] = 1;
            targets[2] = 2;
            break;         
    }
    
    srand(time(NULL) + rank * 100);
    int msg_size;
    int target;
    int random;
    char dummy_send[MAX_STRING_LEN];
    char dummy_recv[MAX_STRING_LEN];
    
    MPI_Request req;
   // MPI_Irecv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &persistent_req);


    for(int i = 0; i < NUM_MSGS; i++){
        MPI_Irecv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &req);
        target = targets[i%3];

        random = rand()%100;

        if(random < 50){
            msg_size = 16;
        }
        if(random < 90){
            msg_size = 512;
        }
        else{
            msg_size = 5000;
        }
        for(int i = 0; i<msg_size; i++){
            dummy_send[i] = "abcdefghijklmnopqrstuvwxyz"[rand()%26];
        }
       // MPI_Request req;

       // MPI_Irecv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &req);

        printf("[rank %d] sending %d bytes to %d (iter %d)\n", rank, msg_size, target, i);
        fflush(stdout);
        MPI_Send(dummy_send, msg_size, MPI_CHAR, target, 0, MPI_COMM_WORLD);
    
        MPI_Wait(&req, MPI_STATUS_IGNORE);
        //MPI_Wait(&req, MPI_STATUS_IGNORE);
        printf("[rank %d] iter %d: received message\n", rank, i);
       // MPI_Irecv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &persistent_req);
    }

    MPI_Finalize();
    return 0;
}