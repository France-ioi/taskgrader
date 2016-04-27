# Taskgrader

The taskgrader tool manages every step of grading a contest task, from the generation of test data to the grading of a solution output.

It allows for a wide variety of contest task types and languages to be evaluated, and is meant to be used both locally for tests and in contest evaluation settings.

It uses [isolate](https://github.com/ioi/isolate) as a sandbox to run solutions to limit execution time and memory, as well as their access to the environment.

**This documentation covers:**

* Getting started:
    * [Installation](install.md)
    * [Basic usage](basicusage.md) and basic usage
    * [How to write tasks](writing.md) for use with the taskgrader
* Reference:
    * [taskSettings.json](tasksettings.md), the settings for auto-detection of the task components and parameters
    * [defaultParams.json](defaultparams.md), the full description of the task for direct use by evaluation processes
* [Error messages](errors.md) and their meaning
* [Further information](moreinfo.md) on the taskgrader internals
