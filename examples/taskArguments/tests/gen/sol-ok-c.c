#include <stdio.h>

int main(int argc, char *argv[]) {
    int a;
    double b;
    sscanf(argv[1], "%d", &a);
    sscanf(argv[2], "%lf", &b);
    printf("%d %.2lf", a, b);
    return 0;
}
