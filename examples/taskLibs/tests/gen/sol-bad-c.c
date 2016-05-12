#include "lib.h"

// This solution is an invalid C solution.
// (gives the maximum instead of the minimum)

int main() {
    int m = getNumber(0);
    int i;
    for(i=1; i<nbNumbers(); i++)
    {
        int n = getNumber(i);
        if(n > m)
        {
            m = n;
        }
    }
    printf("%d\n", m);
    return 0;
}
