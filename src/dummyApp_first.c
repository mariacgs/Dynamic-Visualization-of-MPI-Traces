#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include <stdbool.h>
#include <time.h>

#define MAX_STRING_LEN (64*1024*1024) 
#define NUM_MSGS 3000

int main(int argc, char** argv){
    MPI_Init(&argc, &argv);

    int size, rank;
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    int targets[size-1];
    int target = rank +1;

    for(int i = 0; i < size -1; i++){
        if (target == size){
            target = 0;
        }

        targets[i] = target;
        target ++;
    }

    srand(time(NULL) + rank * 100);
    int msg_size;
    int random;
    char* dummy_send = malloc(MAX_STRING_LEN);
    char* dummy_recv = malloc(MAX_STRING_LEN);
    
    MPI_Request req;
   // MPI_Irecv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &persistent_req);

    int sender = rank - 1;
    if(rank == 0){
        sender = size - 1;
    }

    printf("this is beggining and my sender is: %d\n", sender);

    for(int i = 0; i < NUM_MSGS; i++){
        int index = i%(size-1);
        target = targets[index];
        random = rand()%100;

        if(random < 50){
            msg_size = 16 * 1024 * 1024;
        }
        else if(random < 90){
            msg_size = 32 * 1024 * 1024;
        }
        else{
            msg_size = 64 * 1024 * 1024;
        }

        if (msg_size > MAX_STRING_LEN) {
            printf("Error: msg_size exceeds buffer size!\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        for(int j = 0; j<msg_size; j++){
            dummy_send[j] = "abcdefghijklmnopqrstuvwxyz"[rand()%26];
        }

        // Post receive first
        MPI_Irecv(dummy_recv, MAX_STRING_LEN, MPI_CHAR, sender, MPI_ANY_TAG, MPI_COMM_WORLD, &req);
        
        printf("[rank %d] sending %d bytes to %d (iter %d)\n", rank, msg_size, target, i);
        fflush(stdout);

       // MPI_Barrier(MPI_COMM_WORLD);
        MPI_Send(dummy_send, msg_size, MPI_CHAR, target, 0, MPI_COMM_WORLD);

        if ((i+1)%(size-1) == 0){
            sender = rank - 1;
            if(rank == 0){
                sender = size - 1;
            }
        } else {
            sender --;
            if(sender == -1){
                sender = size-1;
            }
        }

        printf("IT: %d, rank: %d and my sender is: %d\n", i, rank, sender);
    
        MPI_Wait(&req, MPI_STATUS_IGNORE);
        printf("[rank %d] iter %d: received message\n", rank, i);
    }

    free(dummy_send);
    free(dummy_recv);

    MPI_Finalize();
    return 0;
}