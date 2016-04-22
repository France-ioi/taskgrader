#include <iostream>
#include <fstream>
#include <stdio.h>
using namespace std;

/*
  Checking program: checks the output of the solution is the expected output
  Takes three arguments on command-line:
    ./checker test.solout test.in test.out
  where
    test.solout is the solution output
    test.in is the test input given to the solution
    test.out is the expected output (if given by the task, else an empty file)
  If you change the path of the checker, execute
    taskstarter.py add checker [path_to_new_checker]
  to update task settings.
*/

// This is an example checker program, edit it for your task needs.

int main(int argc, char** argv) {
    // Check number of command-line arguments
    if(argc != 4) {
        printf("Error: invalid number of command-line arguments (got %d instead of 3).\n", argc-1);
        // An exit code of 1 indicates a checking error
        return 1;
    }

    // Open the files
    ifstream solAnswer, inputData, refAnswer;
    solAnswer.open(argv[1]);
    inputData.open(argv[2]);
    refAnswer.open(argv[3]);

    // EDIT ME (remove this line once done)

    // EXAMPLE: check the solution answer is the minimum of the 3 values

    // Read the test case
    int a, b, c;
    inputData >> a >> b >> c;
    // Compute the expected answer
    int expected = min(min(a, b), c);

    // Read the solution answer
    int solAnswerInt;
    solAnswer >> solAnswerInt;

    if(solAnswerInt == expected) {
        // The answer is valid, give a grade of 100
        printf("100\n");
        // Exit code of 0 as the checking didn't have any error
        return 0;
    } else {
        // The answer is invalid
        // Give a grade of 0
        printf("100\n");
        // and explain the grade
        printf("Invalid answer: solution answered '%d', expected answer was '%d'.\n", solAnswerInt, expected);
        // Exit code of 0 as the checking didn't have any error
        return 0;
    }
}
