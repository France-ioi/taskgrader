#include "lib.h"

// This solution is a valid C solution.

int main() {
    int m = getNumber(0);
    int i;
    for(i=1; i<nbNumbers(); i++)
    {
        int n = getNumber(i);
        if(n < m)
        {
            m = n;
        }
    }
    printf("%d\n", m);
    return 0;
}
