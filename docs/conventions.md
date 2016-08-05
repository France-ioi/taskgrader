# Conventions

Here are a few conventions used through the tasks and the taskgrader.

## Task structure

By default, a task structure is as follows:

* task-root/
    * tests/
        * files/
            * lib/
                * [compiled language]/
                    * library.h
                * [another compiled language]/
                    * library.hpp
            * run/
                * [interpreted language]/
                    * library.py
            * test01.in
            * test01.out
            * [other librairies]
            * [other test files]
        * gen/
            * gen.sh
            * sanitizer.cpp
            * checker.cpp
            * sol-ok-lang.ext
            * sol-bad-lang.ext
    * [taskSettings.json](tasksettings.md)
    * [defaultParams.json](defaultparams.md) (auto-generated, should not be commited to a repository)

If using this structure, most files will be auto-detected by genJson.

## Build directory structure

When performing an evaluation, the taskgrader will store all files from the evaluation (source files, compiled programs, inputs, outputs) in a build folder (default: `taskgrader/files/builds/`). These build folders follow the following structure:

* \_buildXXXX/
    * generators/
        * [generatorId]/: generator compilation folder
    * generations/
        * [generationId]/: generator execution folder
    * checker/: checker compilation folder
    * sanitizer/: sanitizer compilation folder
    * libs/: folder with all libraries (generated or given directly by the task)
        * lib1.ext
        * [other libraries]
    * tests/: folder with all test cases (generated or given directly by the task)
        * test01.in
        * test01.out
        * [other test files]
    * solutions/
        * [solutionId]/: solution compilation folder
    * executions/
        * [solutionId].[executionId]/: solution execution folder
            * solution.exe: compiled solution
            * sanitizer.exe: compiled sanitizer
            * checker.exe: compiled checker
            * test1.in: test case (input)
            * test1.out: test case (expected output)
            * test1.solout: solution answer to the test case
            * test1.solerr: stderr from the solution on that test case
            * test1.cout: checker output (if multicheck is active)
            * test1.cerr: checker stderr (if multicheck is active)
            * test1.time: checker execution information (if multicheck is active)
            * [other test cases]
            * [other files]

A compilation folder is as follows:

* folder/
    * program.exe: compiled program
    * stdout: output of the compilation
    * stderr: stderr of the compilation
