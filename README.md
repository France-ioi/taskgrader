# Task grader
This simple tool manages every step of grading a contest task, from the generation of test data to the grading of a solution output.

## Installing

Install dependencies: on Debian/stable:

    apt install build-essential sharutils python2.7 asciidoc fp-compiler gcj-4.9

you also need to have a binary called `gcj` (not provided by Debian/stable):

    ln -s /usr/bin/gcj-4.9 /usr/bin/gcj

Execute `install.sh` in the taskgrader directory to install. It will help you install everything. If needed, modify `config.py` to suit your needs.

## Executing
The taskgrader itself can be executed with

    python taskgrader.py

It will wait for an input JSON on its standard input, then proceed to evaluation and then output the result JSON on standard output. Read `schema_input.json` and `schema_output.json` for a description of the expected formats.

You can also use the grading tool, executed with

    python grade.py [option]... FILE...

Full usage instructions are given by `grade.py -h`.

## How does it work?

Here's a description of the evaluation process, managed by the function `evaluation(evaluationParams)`.

* `evaluationParams` is the input JSON
* A build folder is created for the evaluation
* The `defaultParams.json` file from the task is read and its variables added
* A `dictWithVars` is created to add the variables, and returns the JSON data as if variables were replaced by their values
* `generators` are compiled
* `generations` describe how `generators` are to be executed in order to generate all the test files
* Some `extraTests` are "manually" added into the tests pool
* The `sanitizer` and the `checker` are compiled
* The `solutions` are compiled
* For each `execution`, we check whether the test file passes the `sanitizer` test, then we execute the solution with the test file as standard input and save the output, and we use the `checker` to grade the solution
* We return the evaluation report

## Evaluation components

The evaluation is made against a task which has multiple components.

### Generators

The `generators` are generating the testing environment. They are executed, optionally with various parameters, to generate files, which can be:

* test files: inputs for the solution, and if necessary, expected results
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

## Grading a solution

`grade.py` allows to grade easily a solution. The task path must be the current directory, or must be specified with `-p`. It will expect to have a `defaultParams.json` file in the task directory, describing the task with some variables.

The `defaultParams.json` must be JSON data pairing the following keys with the right objects:

* `rootPath`: the root path of the files
* `defaultGenerator`: a default generator
* `defaultGeneration`: the default generation for the default generator
* `extraTests` (optional): some extra tests
* `defaultSanitizer`: the default sanitizer
* `defaultChecker`: the default checker
* `defaultDependencies-[language]` (optional): default dependencies for that language; if not defined, it will fallback to `defaultDependencies` or to an empty list
* `defaultFilterTests-[language]` (optional): default glob-style filters for the tests for that language; if not defined, it will fallback to `defaultFilterTests` or to an empty list

## Internal functions (for developers)

`evaluation` is the evaluation process. It reads an input JSON and builds a `dictWithVars` out of it to reflect the variables system. It compiles and executes with the functions `cachedExecute` and `cachedCompile`. These functions need the informations from the function `getCacheDir` to know whether some results are already cached; if there are some, they fetch files from the cache, else they call their counterparts `execute` and `compile` to actually execute and compile. `compile` uses `getFile` to fetch the source and dependency files into the working directory. `execute` uses `capture` to save the contents of a file into a `captureReport` in the output JSON.
