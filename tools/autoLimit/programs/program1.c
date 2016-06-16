// This program is not meant to be time nor memory efficient.
// It is a reference program doing computations and using memory.

#include <stdio.h>
#include <stdlib.h>

#define MAX_NUMBER 100000

int main() {
    int i, j;
    int primes[MAX_NUMBER];
    for (i=2; i<MAX_NUMBER; i++) {
        primes[i-1] = 0;
        for (j=2; j<=i; j++) {
            if (j == i) {
                printf("%d ", i);
                primes[i-1] = 1;
            } else if (i % j == 0) {
                break;
            }
        }
    }
    printf("are primes.\n");
    return 0;
}
