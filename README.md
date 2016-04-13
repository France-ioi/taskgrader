# Task grader
This tool manages every step of grading a contest task, from the generation of test data to the grading of a solution output.

It is meant to be used both locally for tests and in contest evaluation settings.

## Installing

### Dependencies

You first need to install a few dependencies; on Debian/stable, the required dependencies are:

    apt-get install build-essential python2.7

Some additional dependencies are required to support all languages:

    apt-get install fp-compiler gcj-4.9 git nodejs php5-cli python3

Some systems don't provide the `gcj` shortcut, in that case make a symlink to your version of `gcj`, such as:

    ln -s /usr/bin/gcj-4.9 /usr/bin/gcj

#### Control groups (for contest environments)

In a contest environment, you may want control groups enabled in your kernel:

    apt-get install cgroup-tools

On some kernels, you might need to (re)activate the memory subsystem of control groups (on Debian, you can check whether the folder `/sys/fs/cgroup/memory` is present).

You can do this by using the `cgroup_enable=memory` kernel option. On many systems, you can do that by editing `/etc/default/grub` to add:

    GRUB_CMDLINE_LINUX="cgroup_enable=memory"

and then executing `update-grub` as root. Once enabled, set `CFG_CONTROLGROUPS` to `True` in `config.py` (after installation) to enable their usage within the taskgrader.

Some more information can be found in the [isolate man page](http://www.ucw.cz/moe/isolate.1.html).

### Installation

Execute `install.sh` in the taskgrader directory to install, as the user who will be running the taskgrader. It will help you install everything.

If needed, edit `config.py` to suit your needs; however default values will work for simple tests.

### Testing

After configuration, you can test that the taskgrader is configured properly and is behaving as expected by running `tests/test.py`. By default, it will run all tests and give you a summary. Full usage instructions are given by `test.py -h`.

If you didn't install dependencies for all languages, some tests will fail.

## Executing

The taskgrader itself can be executed with

    python taskgrader.py

It will wait for an input JSON on its standard input, then proceed to evaluation and then output the result JSON on standard output. Read `schema_input.json` and `schema_output.json` for a description of the expected formats. Various tools described later can help you write this input JSON.

Verbosity options are available, use `taskgrader.py -h` for more help.

## Example usage

Some commands you can try:

    ./taskgrader.py < examples/testinput.json
    ./taskgrader.py < examples/testinput.json | tools/stdGrade/summarizeResults.py

First command will execute the taskgrader on an example evaluation described by `examples/testinput.json`; it will output the result JSON, which isn't very human-readable. The second command will pass that output JSON to `summarizeResults.py`, a simple tool to show the results in a more human-readable way.

    tools/taskstarter/taskstarter.py init mynewtask

This command will start a new task in the folder `mynewtask`; use it if you want to write a task. In this new task folder, you'll find a few files to guide you on the usual components of a task. The next section describes that in more detail.

    cd examples/task3 ; ../../tools/taskstarter/taskstarter.py test

A task may be tested as shown with this command. Here it will test the example `task3`.

More details on usage can be found through this documentation.

## Getting started on writing a task

A "task" is a set of programs and files representing the problem the solutions will be evaluated against:

* the test cases (input files and the associated expected output),
* the libraries the solutions can use
* an optional generator which generates these two types of files
* a sanitizer, checking the input files are in the required format
* the checker, grading each solution's output

The script `tools/taskstarter/taskstarter.py` can assist with writing a task.

Here are some examples based around a simple problem: the program is given a number as input, and must output the double of the number. These example tasks can be found in the `examples` folder.

### Example 1: only test cases

A task can be just test cases. The task can be built and tested like this:

* We start our task in a folder with `taskstarter.py init`; it will give us a base task structure we can use as reference
* We put the test cases input files `test1.in` and `test2.in` in the subfolder `tests/files/`
* We put in the same subfolder `test1.out` and `test2.out`, the correct output of these test cases
* We can write a valid solution, for instance `sol-ok-c.c` in this example
* We can test this solution with `taskstarter.py testsol tests/gen/sol-ok-c.c`, it will say the solution got a grade of 100 for each test

When the task is only test cases, the tools will use default programs as sanitizer and checker. The solution will get a perfect grade (100) if its output is the expected output (`test1.out` for the test case `test1.in`, ...), or a 0 grade if its output is different.

We can add our solution to the "correct solutions" with `taskstarter.py addsol -g 100 -l c tests/gen/sol-ok-c.c`. It means that each time we'll test the task, the solution will be tested against the task, and `-g 100` means we expect the solution to get a grade of 100 each time. It allows to test against regressions, that is to say that after modifications, that the task still gives the right grade to our known solutions.

We can finally test the task with `taskstarter.py test`.

*This example can be found in the `examples/task1` folder.*

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

### Example 3: adding a generator

It can be handy to use a generator to generate the test cases and/or libraries for the task, instead of writing them all by hand.

We add a generator like this:

* We use the task made in the last example
* We write a script `gen.sh` which generates the files upon execution; it must be a shell script, and it must write the files following the same tree as the `files` folder
* We add the generator to the task with `taskstarter.py add generator tests/gen/gen.sh`
* Finally, we test the task with `taskstarter.py test`.

The generator is handy when a large number of test cases must be generated, and also for complex tasks where the expected output can take a long time to be computed, and thus needs to be precomputed.

*This example can be found in the `examples/task3` folder.*

### Testing tasks

Tasks can be tested with:

* `taskstarter.py test`, which will use the tool `genJson` to prepare the task for usage (read about `defaultParams.json` file below for more information) and test it for valid compilation, and test that the "correct solutions" get the expected grades.
* `taskstarter.py testsol [SOLUTION.c]`, which if the task is valid, will test `SOLUTION.c` against the task. It is meant for quick solution testing; it uses the `stdGrade` tool.

### Using tasks

The tool `genJson`, automatically called when using `taskstarter.py test`, prepares the task by writing its parameters into a `defaultParams.json` file. It contains all the required information to evaluate solutions against the task, and can be used by evaluation platforms directly to reference the task. The tool `stdGrade` will use this file to quickly evaluate solutions.

### Complex task writing

More complex tasks can be written for usage with the taskgrader, but this section and the `taskstarter` tool are meant for simple tasks. More complex options are available in the taskgrader, read the rest of this documentation for more information.

## How does it work?

Here's a description of the evaluation process, managed by the function `evaluation(evaluationParams)`.

* `evaluationParams` is the input JSON
* A build folder is created for the evaluation
* The `defaultParams.json` file from the task is read and its variables added
* A `dictWithVars` is created to add the variables, and returns the JSON data as if variables were replaced by their values
* `generators` are compiled
* `generations` describe how `generators` are to be executed in order to generate all the test files and optional libraries
* `extraTests` are added into the tests pool
* The `sanitizer` and the `checker` are compiled
* The `solutions` are compiled
* All `executions` are done for the solutions
* The full evaluation report is returned on standard output

### Executions

Each execution is the grading of one solution against multiple test files. For each `execution`:
* Test files corresponding to `filterTests` are selected, then for each test file:
* It passes first the `sanitizer` test
* Then the solution is executed, with the test file as standard input and the output saved
* Finally the `checker` grades the solution according to its output on that particular test file

`filterTests` is a list of globs (as `"test*.in"` or `"mytest.in"`) selecting test files to use among all the test files generated by the generators, and the `extraTests` given. One can specify directly test files into this array to use only specific ones.

## Evaluation components

The evaluation is made against a task which has multiple components.

### Generators

The `generators` are generating the testing environment. They are executed, optionally with various parameters, to generate files, which can be:

* test files: inputs for the solution, and if necessary, expected output results
* libraries, for the compilation and execution of solutions

Some of these files can be passed directly in the evaluation JSON, without the need of a generator.

### Sanitizer

The `sanitizer` checks whether a test input is valid. It expects the test input on its stdin, and its exit code indicates the validity of the data.

### Checker

The `checker` checks whether the output of a solution corresponds to the expected result. It expects three arguments on the command line:

* `test.solout` the solution output
* `test.in` the reference input
* `test.out` the reference output

All checkers are passed these three arguments, whether they use it or not. The checker outputs the grading of the solution; its exit code can indicate an error while checking (invalid arguments, missing files, ...).

## Tools

Various tools are available in the subfolder `tools`. They can be configured with their respective `config.py` files.

### Creating a task

`taskstarter.py` helps task writers create and modify simple tasks. This simple tool is meant as a starting point for people not knowing how the taskgrader works but willing to write a task, and helps them through documented steps. It allows to do some operations in tasks folders, such as creating the base skeleton, giving some help on various components and testing the task. This tool creates a `taskSettings.json` in the task folder, that `genJson.py` can then use to create a `defaultParams.json` accordingly. Read the "Getting started on writing a task" section for more information.

### Preparing a task for grading

`genJson.py` analyses tasks and creates the `defaultParams.json` file for them. It will read the `taskSettings.json` file in each task for some settings and try to automatically detect other settings.

#### taskSettings.json

The `taskSettings.json` is JSON data giving some parameters about the task, for use by `genJson.py`. It has the following keys:

* `generator`: path to the generator of the task
* `generatorDeps`: dependencies for the generator (list of fileDescr, see the input JSON schema for more information)
* `sanitizer`, `sanitizerDeps`, `sanitizerLang`: sanitizer of the task (path, dependencies, language; default is no dependencies and auto-detect language depending on extension)
* `checker`, `checkerDeps`, `checkerLang`: checker of the task (path, dependencies, language; default is no dependencies and auto-detect language depending on extension)
* `extraDir`: folder with extra files (input test files and/or libraries)
* `overrideParams`: JSON data to be copied directly into `defaultParams.json`, will replace any key with the same name from `genJson.py` generated JSON data
* `correctSolutions`: list of solutions known as working with the task, will be tested by `genJson.py` which will check whether they get the right results. Each solution must have the following keys: `path`, `lang` and `grade` (the numerical grade the solution is supposed to get).

#### defaultParams.json

The `defaultParams.json` is a task file giving some information about the task, must be JSON data pairing the following keys with the right objects:

* `rootPath`: the root path of the files
* `defaultGenerator`: a default generator
* `defaultGeneration`: the default generation for the default generator
* `extraTests` (optional): some extra tests
* `defaultSanitizer`: the default sanitizer
* `defaultChecker`: the default checker
* `defaultDependencies-[language]` (optional): default dependencies for that language; if not defined, it will fallback to `defaultDependencies` or to an empty list
* `defaultFilterTests-[language]` (optional): default glob-style filters for the tests for that language; if not defined, it will fallback to `defaultFilterTests` or to an empty list

### Grading a solution

`stdGrade.sh` allows to easily grade a solution. The task path must be the current directory, or must be specified with `-p`. It will expect to have a `defaultParams.json` file in the task directory, describing the task with some variables. Note that it's meant for fast and simple grading of solutions, it doesn't give a full control over the evaluation process. `stdGrade.sh` is a shortcut to two utilities present in its folder, for more options, see `genStdTaskJson.py -h`.

Basic usage: `stdGrade.sh [SOLUTION]...` from a task folder.

## Error messages

### Isolate is not properly installed

This error message happens when `isolate`, the tool used to isolate solution executions and gather metrics, was not properly installed. The taskgrader will fall back to a normal execution, which means the execution will not be isolated (allowing the solution to access the whole filesystem, or communicate over the network, for instance), and the taskgrader will not be able to tell how much time and memory the execution used. It's okay for a test environment, but `isolate` needs to be configured properly for a contest environment.

The script `install.sh` normally takes care of installing `isolate` properly; if not, try launching it again and looking for any error message related to `isolate`.

### Unable to import jsonschema

The taskgrader uses [jsonschema](https://github.com/Julian/jsonschema) for input and output JSON validation. It should normally be downloaded by the `install.sh` script, but it may fail if `git` is not installed. This validation is not mandatory, but if the input JSON is not valid, the taskgrader will most likely crash. The validation helps knowing which JSONs are invalid and why.

If `pip` is available, you can install jsonschema automatically with `pip install jsonschema`, alternatively you can download it manually from the [jsonschema GitHub repository](https://github.com/Julian/jsonschema).

## Internals (for developers)

`evaluation` is the evaluation process. It reads an input JSON and preprocesses it to replace the variables.

Each program is defined as an instance of the class Program, that we `compile`, then `prepareExecution` to set the execution parameters, then `execute` with the proper parameters.

Languages are set as classes which define two functions: `getSource` which defines how to search for some dependencies for this language, and `compile` which is the compilation process.

The cache is handled by various Cache classes, each storing the cache parameters for a specific program and giving access to the various cache folders corresponding to compilation or execution of said programs.
