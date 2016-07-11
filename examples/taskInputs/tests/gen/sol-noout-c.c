#include <stdio.h>
#include <stdlib.h>

// This solution is an invalid C solution (not writing any 'output' file).

int main() {
    int k;
    FILE *fin;

    fin = fopen("input", "r");
    fscanf(fin, "%d", &k);
    fclose(fin);

    return 0;
}
