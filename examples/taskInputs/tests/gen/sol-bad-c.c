#include <stdio.h>
#include <stdlib.h>

// This solution is an invalid C solution.

int main() {
    int k;
    FILE *fin, *fout;

    fin = fopen("input", "r");
    fscanf(fin, "%d", &k);
    fclose(fin);

    fout = fopen("output", "w");
    fprintf(fout, "%d\n", k*3);
    fclose(fout);

    return 0;
}
