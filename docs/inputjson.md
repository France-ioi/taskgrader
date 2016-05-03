# Input JSON

This page describes the *input JSON*, which is the JSON data sent to the taskgrader (on its standard input) to specify the full evaluation process.

This page is currently under writing, but you can check the input JSON format in the file `schema_input.json`.

## Simplified version

*Writing in progress*

With the genJson tool, you can generate for each task a [`defaultParams.json` file](defaultparams.md) which will contain default values for evaluations against that task. Once a task has its defaultParams generated, you can evaluate a solution with a simple input JSON like this:

    {
        "rootPath": "/some/path",
        "taskPath": "/path/to/the/task",
        "extraParams": {
            "solutionFilename": "solution.c",
            "solutionPath": "/home/user/solution.c",
            "solutionLanguage": "c",
            "solutionDependencies": "@defaultDependencies-c"
    }}
