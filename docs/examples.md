# Examples index

The taskgrader comes with various examples depicting features of the taskgrader. Each of these examples is described in detail in this page.

Name | Description
---- | -----------
taskCChecker | Check the output of the solution compilation
taskGenerator | Generate test cases with a *generator* script
taskInputs | Have the solution read a specific file then output in another file, instead of stdin/stdout
taskLibs | Add libraries for usage by the solutions
taskMaths | Count the number of math operations performed
taskMinimal | Minimal task with only test cases and expected outputs
taskRunner | Run a Python function defined by the solution instead of a full program
taskSets | Separate multiple sets of tests
taskSolchecker | Read the solution source (to check for length)
taskTestchecker | Solution is not a program but a set of test cases
taskTools | Custom sanitizer and checker
taskTurtle | Check a turtle program and output its display


# Basic examples

Here are some basic examples based around a simple problem: the program is given a number as input, and must output the double of the number. These example tasks can be found in the `examples` folder.

## Minimal example: only test cases (taskMinimal)

A task can be just test cases and their corresponding expected outputs. The task can be built and tested like this:

* We start our task in a folder with `taskstarter.py init` (answering 'no' to all questions); it will give us a base task structure we can use as reference
* We put the test cases input files `test1.in` and `test2.in` in the subfolder `tests/files/`
* We put in the same subfolder `test1.out` and `test2.out`, the correct output of these test cases
* We can write a valid solution, for instance `sol-ok-c.c` in this example
* We can test this solution with `taskstarter.py testsol tests/gen/sol-ok-c.c`, it will say the solution got a grade of 100 for each test

When the task is only test cases, the tools will use default programs as sanitizer and checker. The solution will get a perfect grade of 100 if its output is the expected output (`test1.out` for the test case `test1.in`, ...), or the minimum grade of 0 if its output is different.

*This example can be found in the `examples/taskMinimal` folder.*

## Adding correct solutions to our task

Once our task is almost ready, we can add "correct solutions": they are known solutions which have known results, such as always giving a good answer or always giving a bad answer.

It allows to test against regressions, that is to say that after modifications, that the task still gives the right grade to our known solutions.

Using again our example task 1, we can add correct solutions like this:

    taskstarter.py addsol -g 100 -l c tests/gen/sol-ok-c.c

It means that each time we'll test the task, the solution `sol-ok-c.c` will be automatically evaluated against the task, and `-g 100` means we expect the solution to get a perfect grade of 100 each time (and having a final average grade of 100).

We can also add an invalid solution, that is to say, a solution who will get the minimum grade of 0 each time. In this example, we have such a solution, `sol-bad-c.c`. We add it as a "bad solution" like this:

    taskstarter.py addsol -g 0 -l c tests/gen/sol-bad-c.c

which means that we expect it to get a grade of 0 on each test (hence a final expected average grade of 0).

We can finally test the task by executing, in the task folder,

    taskstarter.py test

in the task folder. It will output:

    Test successful on 2 correctSolutions with up to 2 test cases.

which means the task successfully compiled, that the evaluation of the good solution `sol-ok-c.c` got a perfect grade of 100 each time, and that the evaluation of the bad solution `sol-bad-c.c` got a bad grade of 0 each time.


## Tools example: adding a sanitizer and a checker (taskTools)

It's generally recommended to use a sanitizer and a checker: the sanitizer will ensure only valid input test files are given to solutions, especially in cases where contestants are allowed to use their own test files as examples; the checker can give a more precise grade to solutions, and also handle cases where the solution output is not in the exact format expected.

We add a sanitizer and a checker to our test like this:

* We use the task made in the last example
* We write a script `sanitizer.sh` which takes as input the test case, and sets its exit code to 0 if it's valid, 1 if it's not
* We write a script `checker.sh` which takes three arguments, `test.in` the test case input, `test.solout` the solution output, `test.out` the reference (expected) output; and gives a grade to the solution based on its output
* We add the sanitizer and the checker to the task with `taskstarter.py add checker tests/gen/checker.sh` and `taskstarter.py add sanitizer tests/gen/sanitizer.sh`
* Finally, we test the task with `taskstarter.py test`. It will tell us whether our programs were detected, compiled and executed successfully, and whether the "correct solution" we defined passed the test and got the expected grade of 100.

The sanitizer and the checker can be written in any language supported by the taskgrader.

*This example can be found in the `examples/taskTools` folder.*


## Libs example: adding libraries (taskLibs)

This example is a task with libraries intended for usage by solutions. It's pretty simple to add libraries:

* We write a library `lib.h` intended for usage with solution in the C language
* We put it in `tests/files/lib/c/lib.h`
* Finally, we test the task with `taskstarter.py test`.

As long as the libraries are in the right folder (by default, `tests/files/lib/[language]/[library.ext]`), they will be automatically detected by `genJson` and added to the default dependencies for that language. All solutions of that language will have the library available for importation without any configuration necessry.

*This example can be found in the `examples/taskLibs` folder.*


## Generator example: adding a generator (taskGenerator)

It can be handy to use a generator to generate the test cases and/or libraries for the task, instead of writing them all by hand.

We add a generator like this:

* We use the task made in the last example
* We write a script `gen.sh` which generates the files upon execution; it must be a shell script, and it must write the files following the same tree as the `files` folder
* We add the generator to the task with `taskstarter.py add generator tests/gen/gen.sh`
* Finally, we test the task with `taskstarter.py test`.

The generator is handy when a large number of test cases must be generated, and also for complex tasks where the expected output can take a long time to be computed, and thus needs to be precomputed.

Note that the auto-test with `taskstarter.py test` will show:

    Test successful on 2 correctSolutions with up to 4 test cases.

which means the taskgrader successfully found all 4 test cases, the 2 test cases given directly in the task folder, and the 2 test cases generated by our script `gen.sh`.

*This example can be found in the `examples/taskGenerator` folder.*


## Test sets example: having multiple executions with different test sets (taskSets)

In some tasks, we can have test sets which are testing different aspects of the task. We can set the default to be evaluating each set separately, for instance when we want to have an average grade for each set of tests and not all tests at once.

It can be done by editing the `taskSettings.json` file and adding a `defaultEvaluationExecutions` key describing each test set:

    "defaultEvaluationExecutions": [
        {"id": "test-positive",
        "idSolution": "@solutionId",
        "filterTests": ["testpos1.in", "testpos2.in", "testpos3.in"],
        "runExecution": "@defaultSolutionExecParams"
        },
        {"id": "test-negative",
        "idSolution": "@solutionId",
        "filterTests": ["testneg1.in", "testneg2.in"],
        "runExecution": "@defaultSolutionExecParams"
        },
        {"id": "test-all",
        "idSolution": "@solutionId",
        "filterTests": ["test*.in"],
        "runExecution": "@defaultSolutionExecParams"
        }]
    }

Here we have three test sets, `test-positive`, `test-negative` and `test-all`, the first one using only positive tests, the second one using only negative tests, and the last one using all test cases.

Note that if the cache is enabled, the solution will not be executed again for the `test-all` set as all test cases have already been evaluated. Instead, the taskgrader will just fetch back the results from the cache.

*This example can be found in the `examples/taskSets` folder.*


# More complex task writing

More complex tasks can be written for usage with the taskgrader. The `taskstarter` tool is meant for simple tasks, you need to edit files manually for these examples. Here is an example, but read the rest of this documentation for more information.

## Runner example: solution skeleton (taskRunner)

Sometimes, the "solution" to be evaluated is not the file to be executed, but a library or a test file.

In this example, we have `runner.py` calling the function `min3nombres` from the user-sent python file. The "solution" is hence a library, and the actual script executed is `runner.py` using this library.

In order to be able to evaluate solutions against this task, we add, in `taskSettings.json`, the key `defaultEvaluationSolutions`. This key will get copied directly to `defaultParams.json`, where it will indicate the skeleton of what needs to be executed by the taskgrader. Some more information can be found in the [`defaultParams.json` reference](defaultparams.md). Here this key contains:

    "defaultEvaluationSolutions": [{
        "id": "@solutionId",
        "compilationDescr": {
            "language": "python",
            "files": [{"name": "runner.py",
                       "path": "$TASK_PATH/tests/gen/runner.py"}],
            "dependencies": [{"name": "solution.py",
                              "path": "@solutionPath",
                              "content": "@solutionContent"}]
            },
        "compilationExecution": "@defaultSolutionCompParams"}]

This example means to use `runner.py` as script to execute (hence in "files"), and to give the solution as dependency, stored in `solution.py` (whichever the original solution filename is, it will be renamed to `solution.py`).

In this key, we indicate what needs to be executed, and the values `'@solutionFilename', '@solutionLanguage', '@solutionDependencies', '@solutionPath', '@solutionContent'` will be replaced with the solution's name, language, dependencies, and its path or content. In this example task, `runner.py` is defined as the main program to execute, and our solution is passed as dependency of this program, and automatically named `solution.py` to be then imported by `runner.py`.

You can test the task by running, from the task folder:

* `taskstarter.py test` for the normal test
* `taskstarter.py testsol tests/gen/sol-ok-py.py` for a good solution
* `taskstarter.py testsol tests/gen/sol-bad-py.py` for a bad solution

The testing tool `stdGrade` will automatically understand how to evaluate these solutions.

*This example can be found in the `examples/taskRunner` folder.*


## Another runner example: counting the number of mathematical operations

In this example, we count the number of mathematical operations to make sure the solution doesn't do too many. To do this, we use a runner which modify the execution environment of the solution : it will replace the `int` function by one returning a `Number` class. This class is a custom class allowing us to count the number of operations and block some operations from being used (in this example, only addition and substraction are allowed, multiplication and division aren't).

The runner outputs the statistics at the end of the script, which are then read back by the checker.

*This example can be found in the `examples/taskMaths` folder.*


## Solution checker example: reading the solution source (taskSolchecker)

In this task, the checker grades the solution source code.

For this example, the checker counts the number of characters of the solution (excluding comment lines and whitespaces), and gives a lower grade if the solution source is too long. (Of course it gives a grade of 0 if the solution doesn't output the correct answer.)

In order to have the checker be able to read the solution source, we use the `addFiles` key of its `runExecution` params; this key allows to add any file in the working folder during an execution. Here, it adds to the checker execution an access to the solution source, stored in file `solution`. The checker can then read this file, along with the test case files, to accordingly grade the solution.

Here, we modify the key `defaultChecker` in order to add the file, like this:

    "defaultChecker": {
        "compilationDescr": {
            "language": "python2",
            "files": [{
                "name": "checker.py",
                "path": "$TASK_PATH/tests/gen/checker.py"
                }],
            "dependencies": []},
        "compilationExecution": "@defaultToolCompParams",
        "runExecution": {
            "memoryLimitKb": 131072,
            "timeLimitMs": 60000,
            "useCache": true,
            "stdoutTruncateKb": -1,
            "stderrTruncateKb": -1,
            "addFiles": [{
                "name": "solution",
                "path": "@solutionPath",
                "content": "@solutionContent"
                }],
            "getFiles": []}}
    }

You can test the task by running, from the task folder:

* `taskstarter.py test` for the normal test, which will check each solution has the expected grade
* `taskstarter.py testsol tests/gen/sol-ok-c.c` for a good and short solution getting the perfect grade of 100 (right answer, less than 60 characters)
* `taskstarter.py testsol tests/gen/sol-long-c.c` for a solution too long getting a grade of 93 (right answer, more than 60 characters)
* `taskstarter.py testsol tests/gen/sol-bad-c.c` for a bad solution getting a grade of 0 (wrong answer)

*This example can be found in the `examples/taskSolchecker` folder.*


## Compilation checker example: reading the compiler output (taskCChecker)

In this task, the checker reads the compiler output. It then, as an example, displays it on his grading output; a more detailed checker could though read the compiler output to check for specific errors.

This is done by using again the `addFiles` key as done in the previous example, and adding the compiler output in the files to give to the checker:

    "addFiles": [
      {
        "name": "compilationStdout",
        "path": "$BUILD_PATH/solutions/solution/stdout"
      }, {
        "name": "compilationStderr",
        "path": "$BUILD_PATH/solutions/solution/stderr"
      }]

This will give the checker access to the compilation output through the files `compilationStdout` and `compilationStderr`.

*This example can be found in the `examples/taskCChecker` folder.*


## Specific input/output files examples (taskInputs)

In this task, the solution has to read from a file named `input`, and write its answer to the file `output`.

This is done, like previous examples, by using the `addFiles` key, to add for each test a new file `input` containing the new input we want to give to the solution.

In the `taskSettings.json` file, we use the `defaultEvaluationExecutions` to specify each test: set the contents of the `input` file, and specify we want to capture the file `output` (optional, allows to get its contents in the output JSON but unneeded for the checker to have access to this file).

*This example can be found in the `examples/taskInputs` folder.*


## Turtle example: using and saving graphics (taskTurtle)

In this task, the solution is a [turtle](https://docs.python.org/2/library/turtle.html) script; here, its task is to simply to go to a specified position (but more advanced criterias can be written).

This task is complex for two reasons:

* the base turtle library needs a graphic window to work (unavailable on an evaluation server), and we still need to "isolate" the solution execution
* we save the resulting image as a PNG file

### Requirements

To work, this task needs:

* Xvfb, "X virtual framebuffer", a X server without display (to make turtle show graphics and then save them)
* PIL, "Python Imaging Library", a library to handle images
* Tkinter, used by the turtle for its graphics
* Ghostscript, for PIL to read the saved output from Tk

On Debian, they can be installed with the following command:

    apt-get install xvfb python-pil python-tk ghostscript

The task also needs the `checker.sh` to be whitelisted for use outside of isolate; this is done by adding its path in `CFG_NOISOLATE` in taskgrader's `config.py` file, for instance:

    CFG_NOISOLATE = ["/path/to/taskgrader/examples/taskTurtle/tests/gen/checker.sh"]

(It must be an absolute path, as returned by Python's `os.path.abspath`.)

### How it works

This task works by saving all turtle commands executed by the solution, and then replaying them to generate the resulting PNG, and also to evaluate the criteria of task completion.

#### runner.py

The execution of solutions is wrapped in a `runner.py` execution.

The runner of this task defines a class, `LoggedTurtle`, which logs all the turtle commands executed while inhibiting their graphics. It also modifies the solution source code to change all instances of the normal `Turtle` class to this `LoggedTurtle` class; and then executes the solution while logging all commands. It finally prints the full JSON-encoded log, whose entries contain the following elements:

* ID number for the turtle (to allow multiple turtles)
* Component, either 'nav' for the navigator, 'turtle' for other functions
* Name of turtle's function called
* args and kwargs of the call

See `turtleToPng.py` or `checker.py` for examples on how to use this log.

#### checker.sh

This script has two sub-components:

* `turtleToPng.py` is a script generating the base64-encoded PNG image resulting from the execution of the turtle
* `checker.py` is the actual checker, using the turtle log to evaluate the criteria and grade the solution

As said above, this script must be whitelisted for executiong outside of isolate by the taskgrader. It will allow the script to run Xvfb and `turtleToPng.py` outside of isolate, as X displays cannot run inside isolate.

It will then use the taskgrader tool `tools/isolate-run.py` to run the actual checker `checker.py` inside isolate.

### Usage

As usual, you can test the task by running, from the task folder:

* `taskstarter.py test` for the normal test, which will check each solution has the expected grade
* `taskstarter.py testsol tests/gen/sol-ok-py.py` for a good solution
* `taskstarter.py testsol tests/gen/sol-bad-py.py` for a bad solution

If you grade a solution against the task, the output JSON will contain a file `turtle_png.b64`, which is the base64-encoded PNG image resulting from each execution of the solution against a test case. It is in the `files` key of each `checker` report (in `/executions[idx]/testReports[idx]`). The file `view.html` in the task folder contains an example JavaScript to display it in a browser.

*This example can be found in the `examples/taskTurtle` folder.*
