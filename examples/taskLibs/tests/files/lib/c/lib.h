#include <stdio.h>

#define MAX_NB 100

int __initDone = 0;
int __numbers[MAX_NB];
int __nbNumbers = 0;

void __init()
{
    if(__initDone == 0)
    {
        int sf, newnb;
        while((sf = scanf("%d", &newnb)) > 0)
        {
            __numbers[__nbNumbers] = newnb;
            __nbNumbers += 1;
        }
        __initDone = 1;
    }
}

int nbNumbers()
{
    __init();
    return __nbNumbers;
}

int getNumber(int idx)
{
    __init();
    if(idx < __nbNumbers)
    {
        return __numbers[idx];
    }
}
