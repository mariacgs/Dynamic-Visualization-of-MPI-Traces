#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include <stdbool.h>

#define MAX_STRING_LEN 1024

int main(int argc, char** argv){
    MPI_Init(&argc, &argv);

    int size, rank;
    int dest1, dest2; 
    
    char dummy_string[1024];

    // 4, 8, 16, 32, 64, 128, 256, 512, 1024
    int msg_size_arr[5] = {3, 15, 63, 255, 1023};
    int msg_size;

    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    //get destinations 
    dest1 = (rank + 2) % size;
    if(size == 2){
        dest1 = (rank + 1) % size;
    }

    dest2 = (rank -1) % size;
    if(dest2<0){
        dest2 = size - 1;
    }
    srand(rank+42);
    msg_size = msg_size_arr[rand()%5];

    for(int i = 0; i<msg_size; i++){
        dummy_string[i] = "abcdefghijklmnopqrstuvwxyz"[rand()%26];
    }

    //define sending string and number
    int dummy_number = rand()%50000;
    char recv_str[MAX_STRING_LEN];
    int recv_number;

    //printf("this is me %d and this is my destination 1: %d\n", rank, dest1);
    //printf("this is me %d and this is my destination 2: %d\n", rank, dest2);

    // Processes send to their destinations
    MPI_Send(dummy_string, strlen(dummy_string)+1, MPI_CHAR, dest1, 0, MPI_COMM_WORLD);

    // receive first message
    MPI_Recv(&recv_str, MAX_STRING_LEN, MPI_CHAR, MPI_ANY_SOURCE, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);

    MPI_Send(&dummy_number, 1, MPI_INT, dest2, 1, MPI_COMM_WORLD);

    MPI_Recv(&recv_number, 1, MPI_INT, MPI_ANY_SOURCE, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    
    MPI_Finalize();
    return 0;
}