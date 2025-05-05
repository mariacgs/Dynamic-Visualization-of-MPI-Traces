#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include <stdbool.h>

#define MAX_STRING_LEN 256

int main(int argc, char** argv){
    MPI_Init(&argc, &argv);

    int size, rank;
    int dest1, dest2;
    
    char dummy_string[256];

    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Request request;
    MPI_Status status;

    //get destinations 
    dest1 = (rank + 2) % size;
    if(size == 2){
        dest1 = (rank + 1) % size;
    }

    dest2 = (rank -1) % size;
    if(dest2<0){
        dest2 = size - 1;
    }

    //define sending string and number
    sprintf(dummy_string, "This is a dummy string. I'm %d sendint a message to %d, there are in total %d processes.", rank, dest1, size);
    int dummy_number = rand()%50000;
    char recv_str[MAX_STRING_LEN];
    int recv_number;

    //printf("this is me %d and this is my destination 1: %d\n", rank, dest1);
    //printf("this is me %d and this is my destination 2: %d\n", rank, dest2);

    // Processes send to their destinations
    MPI_Send(dummy_string, strlen(dummy_string)+1, MPI_CHAR, dest1, 0, MPI_COMM_WORLD);

    // receive first message
    MPI_Irecv(&recv_str, MAX_STRING_LEN, MPI_CHAR, MPI_ANY_SOURCE, 0, MPI_COMM_WORLD, &request);

    MPI_Send(&dummy_number, 1, MPI_INT, dest2, 1, MPI_COMM_WORLD);

    MPI_Recv(&recv_number, 1, MPI_INT, MPI_ANY_SOURCE, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);

    MPI_Wait(&request, &status);
    
    MPI_Finalize();
    return 0;
}