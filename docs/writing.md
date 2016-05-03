# Getting started on writing a task

Use `taskstarter.py init [taskpath]` to interactively create a new task.

A "task" is a set of programs and files representing the problem the solutions will be evaluated against:

* the **test cases** (input files and the associated expected output),
* the **libraries** the solutions can use
* an optional **generator** which generates these two types of files
* a **sanitizer**, validating the input files by checking they are in the required format
* the **checker**, grading each solution's output

The script `tools/taskstarter/taskstarter.py` can assist with writing a task; use `taskstarter.py help` to see the available commands.

Here are some examples based around a simple problem: the program is given a number as input, and must output the double of the number. These example tasks can be found in the `examples` folder.

## Example 1: only test cases

A task can be just test cases. The task can be built and tested like this:

* We start our task in a folder with `taskstarter.py init` (answering 'no' to all questions); it will give us a base task structure we can use as reference
* We put the test cases input files `test1.in` and `test2.in` in the subfolder `tests/files/`
* We put in the same subfolder `test1.out` and `test2.out`, the correct output of these test cases
* We can write a valid solution, for instance `sol-ok-c.c` in this example
* We can test this solution with `taskstarter.py testsol tests/gen/sol-ok-c.c`, it will say the solution got a grade of 100 for each test

When the task is only test cases, the tools will use default programs as sanitizer and checker. The solution will get a perfect grade of 100 if its output is the expected output (`test1.out` for the test case `test1.in`, ...), or the minimum grade of 0 if its output is different.

*This example can be found in the `examples/task1` folder.*

## Adding correct solutions to our task

Once our task is almost ready, we can add "correct solutions": they are known solutions which have known results, such as always giving a good answer or always giving a bad answer.

It allows to test against regressions, that is to say that after modifications, that the task still gives the right grade to our known solutions.

Using again our example task 1, we can add correct solutions like this:

    taskstarter.py addsol -g 100 -l c tests/gen/sol-ok-c.c

It means that each time we'll test the task, the solution `sol-ok-c.c` will be automatically evaluated against the task, and `-g 100` means we expect the solution to get a perfect grade of 100 each time.

We can also add an invalid solution, that is to say, a solution who will get the minimum grade of 0 each time. In this example, we have such a solution, `sol-bad-c.c`. We add it as a "bad solution" like this:

    taskstarter.py addsol -g 0 -l c tests/gen/sol-bad-c.c

which means that we expect it to get a grade of 0 on each test.

We can finally test the task by executing, in the task folder,

    taskstarter.py test

in the task folder. It will output:

    Test successful on 2 correctSolutions with up to 2 test cases.

which means the task successfully compiled, that the evaluation of the good solution `sol-ok-c.c` got a perfect grade of 100 each time, and that the evaluation of the bad solution `sol-bad-c.c` got a bad grade of 0 each time.

### Example 2: adding a sanitizer and a checker

It's generally recommended to use a sanitizer and a checker: the sanitizer will ensure only valid input test files are given to solutions, especially in cases where contestants are allowed to use their own test files as examples; the checker can give a more precise grade to solutions, and also handle cases where the solution output is not in the exact format expected.

We add a sanitizer and a checker to our test like this:

* We use the task made in the last example
* We write a script `sanitizer.sh` which takes as input the test case, and sets its exit code to 0 if it's valid, 1 if it's not
* We write a script `checker.sh` which takes three arguments, `test.in` the test case input, `test.solout` the solution output, `test.out` the reference (expected) output; and gives a grade to the solution based on its output
* We add the sanitizer and the checker to the task with `taskstarter.py add checker tests/gen/checker.sh` and `taskstarter.py add sanitizer tests/gen/sanitizer.sh`
* Finally, we test the task with `taskstarter.py test`. It will tell us whether our programs were detected, compiled and executed successfully, and whether the "correct solution" we defined passed the test and got the expected grade of 100.

The sanitizer and the checker can be written in any language supported by the taskgrader.

*This example can be found in the `examples/task2` folder.*

## Example 3: adding libraries

This example is a task with libraries intended for usage by solutions. It's pretty simple to add libraries:

* We write a library `lib.h` intended for usage with solution in the C language
* We put it in `tests/files/lib/c/lib.h`
* Finally, we test the task with `taskstarter.py test`.

As long as the libraries are in the right folder (by default, `tests/files/lib/[language]/[library.ext]`), they will be automatically detected by `genJson` and added to the default dependencies for that language. All solutions of that language will have the library available for importation without any configuration necessry.

*This example can be found in the `examples/task3` folder.*

## Example 4: adding a generator

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

*This example can be found in the `examples/task4` folder.*

## Testing tasks

Tasks can be tested with:

* `taskstarter.py test`, which will use the tool `genJson` to prepare the task for usage (read about `defaultParams.json` file below for more information) and test it for valid compilation, and test that the "correct solutions" get the expected grades.
* `taskstarter.py testsol [SOLUTION.c]`, which if the task is valid, will test `SOLUTION.c` against the task. It is meant for quick solution testing; it uses the `stdGrade` tool.

## Using tasks

The tool `genJson`, automatically called when using `taskstarter.py test`, prepares the task by writing its parameters into a `defaultParams.json` file. It contains all the required information to evaluate solutions against the task, and can be used by evaluation platforms directly to reference the task. The tool `stdGrade` will use this file to quickly evaluate solutions.

# More complex task writing

More complex tasks can be written for usage with the taskgrader. The `taskstarter` tool is meant for simple tasks, you need to edit files manually for these examples. Here is an example, but read the rest of this documentation for more information.

## Example 5: solution skeleton

Sometimes, the "solution" to be evaluated is not the file to be executed, but a library or a test file.

In this example, we have `runner.py` calling the function `min3nombres` from the user-sent python file. The "solution" is hence a library, and the actual script executed is `runner.py` using this library.

In order to be able to evaluate solutions against this task, we add, in `taskSettings.json`, the key `defaultEvaluationSolutions`. This key will get copied directly to `defaultParams.json`, where it will indicate the skeleton of what needs to be executed by the taskgrader. Some more information can be found in the [`defaultParams.json` reference](defaultparams.md). Here this key contains:

    defaultEvaluationSolutions": [{
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

*This example can be found in the `examples/task5` folder.*
