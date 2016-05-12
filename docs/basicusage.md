# Basic usage

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

This command will start a new task in the folder `mynewtask`; use it if you want to write a task for use with the taskgrader. It will ask you a few questions to guide you through the various components of a task, and write a base task with some example files. The next section describes that in more detail.

    cd examples/taskMinimal ; ../../tools/taskstarter/taskstarter.py test

A task may be tested as shown with this command. Here it will test the example task in folder `taskMinimal`.

More details on usage can be found through this documentation.
