#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <locale.h>

int main() {
    wchar_t c;
    int counta = 0;
    int counte = 0;
    setlocale(LC_ALL, "");
    if(strcmp(setlocale(LC_ALL, NULL), "C") == 0) {
        setlocale(LC_ALL, "UTF-8");
    }
    if(strcmp(setlocale(LC_ALL, NULL), "C") == 0) {
        setlocale(LC_ALL, "en_US.UTF-8");
    }
    if(strcmp(setlocale(LC_ALL, NULL), "C") == 0) {
        setlocale(LC_ALL, "fr_FR.UTF-8");
    }
    while((c = getwchar()) != WEOF) {
        if(c == L'\x00e0') { // à
            counta += 1;
        } else if(c == L'\x00e9') { // é
            counte += 1;
        }
    }
    printf("%d à %d é\n", counta, counte);
    return 0;
}
