#include <iostream>
#include <stdio.h>
using namespace std;

/*
  The sanitizer ensures each test case is valid.
  It is given the test case input on its standard input, and must indicate an
  exit code of 0 if the test case is valid, or 1 if it is invalid to signal the
  taskgrader to not use this test case.
*/

// This is an example sanitizer program, edit it for your task needs.

int main() {
    // EDIT ME (remove this line once done)

    // EXAMPLE: check the test case is 3 integers
    int i;
    int nbValues = 0;

    // Count the number of values
    while(cin >> i) {
        nbValues++;
    }

    if(nbValues == 3) {
        // We got 3 values, return 0 to indicate a valid test case
        return 0;
    } else {
        // We didn't get 3 values, return 1 to indicate an invalid test case
        printf("Error: expected 3 values, got %d instead.\n", nbValues);
        return 1;
    }
}
