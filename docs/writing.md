# Getting started on writing a task

Use `taskstarter.py init [taskpath]` to interactively create a new task.

A "task" is a set of programs and files representing the problem the solutions will be evaluated against:

* the **test cases** (input files and the associated expected output),
* the **libraries** the solutions can use
* an optional **generator** which generates these two types of files
* a **sanitizer**, validating the input files by checking they are in the required format
* the **checker**, grading each solution's output

## First steps

The script `tools/taskstarter/taskstarter.py` can assist with writing a task; use `taskstarter.py help` to see the available commands.

You might start a new task interactively by executing `taskstarter.py init`.

Alternatively, you can also copy one of the [example tasks](examples.md) and use it as a base for your task.

## Testing tasks

Tasks can be tested with:

* `taskstarter.py test`, which will use the tool `genJson` to prepare the task for usage (read about `defaultParams.json` file below for more information) and test it for valid compilation, and test that the "correct solutions" get the expected grades.
* `taskstarter.py testsol [SOLUTION.c]`, which if the task is valid, will test `SOLUTION.c` against the task. It is meant for quick solution testing; it uses the `stdGrade` tool.
* `taskstarter.py testsol -v [SOLUTION.c]`, which will give a more verbose output, showing all the information given by the taskgrader. It can help pinpointing errors.

## Remote testing

If you have access to a [graderqueue](https://github.com/France-ioi/graderqueue) instance, you can evaluate your task through it (for instance, to evaluate on contest servers).

Once you configured the remoteGrader in the file `tools/remoteGrader/config.py` with the URL, login and password to a graderqueue, you can use taskstarter to test remotely.

Once you have tested your task locally, you can use:

    taskstarter.py remotetest [SOLUTION.c]

to test your task and `SOLUTION.c` with a remote server. It will behave as the `testsol` command, except using a remote server instead of the local taskgrader. It will send a "full input JSON", which means that all task files will be contained in the JSON file and the remote server doesn't need any file from your task to evaluate.

If your task is saved/synchronized on the remote server, and the `ROOT_PATH` is configured accordingly (contact your graderqueue/graderserver administrator to know how to configure it), you can test your task with a "simple JSON" with the following command:

    taskstarter.py remotetest -s [SOLUTION.c]

It will send a simple solution with only your solution; the remote server will then read the task files locally for the evaluation. It's thus important that the remote server has the most recent files for the evaluation; if the task are locally and remotely on a SVN repository, taskstarter will check the task has been committed and send the corresponding revision number to the remote server for it to make sure it's on the latest version.

## Using tasks

The tool `genJson`, automatically called when using `taskstarter.py test`, prepares the task by writing its parameters into a `defaultParams.json` file. It contains all the required information to evaluate solutions against the task, and can be used by evaluation platforms directly to reference the task. The tool `stdGrade` will use this file to quickly evaluate solutions.

## Examples

Check the [examples page](examples.md) for a description of the examples in the taskgrader repository. These examples can be easily used as a base for your task.
