# taskSettings.json

The file `taskSettings.json` contains information about the task it is present in, such as its components or its evaluation parameters.

It is used mainly by the genJson tool to generate the [`defaultParams.json` file](defaultparams.md). It is a JSON object containing key-value pairs.

Example *(other examples can be found in the `examples` folder)*:

    {
    "sanitizer": "tests/gen/sanitizer.sh",
    "correctSolutions": [{
        "path": "$TASK_PATH/tests/gen/sol-ok-c.c",
        "language": "c",
        "grade": 100
        }]
    }


The following list is the list of keys it accepts.

## generator, sanitizer, checker

* Name: `generator`, `sanitizer` or `checker`
* Type: `string`
* Example: `"tests/gen/sanitizer.py"`

The keys `generator`, `sanitizer`, `checker` specify the path to each of these three components of the task, relatively to the task path.

### Language

* Name: `sanitizerLang` or `checkerLang`
* Type: `string`
* Example: `"cpp"`

The language of the sanitizer and the checker is normally automatically detected from the file extension, but can be specified manually with these two keys.

### Dependencies

* Name: `generatorDeps`, `sanitizerDeps` or `checkerDeps`
* Type: `object`
* Example: `{"name": "libcheck.py", "path": "$TASK_PATH/tests/gen/libcheck.py"}`

These keys specify the dependencies needed for each of these three components of the task. Each object is a `fileDescr` as defined in the taskgrader's `schema_input.json`.

Note that the generator dependencies are normally automatically detected, if they are in the same folder.

## extraDir

* Name: `extraDir`
* Type: `string`
* Example: `"tests/files/"`

This key specify the folder, relative to the task, to scan for `extraFiles`, that is to say, test cases given as-is, without generator.

## ignoreTests

* Name: `ignoreTests`
* Type: `list of strings`
* Example: `["sample*"]`

This key is a list of glob-style filenames to ignore while scanning for test cases. These test cases will be ignored by genJson, and thus not be used for evaluation.

## correctSolutions

* Name: `ignoreTests`
* Type: `list of objects`
* Example: `[{"path": "$TASK_PATH/tests/gen/sol-ok-c.c", "language": "c", "grade": 100}]`

This key defines the "correct solutions", which are solutions which will be automatically evaluated against the task by genJson, when generating the `defaultParams`. They allow to test the task is behaving properly. It is a list of objects, each having up to 4 keys:

Key name | Type | Description
-------- | ---- | -----------
`path` | required `string` | Path to the solution
`language` | optional `string` | Language of the solution
`grade` | optional `int` or `int list` | Average grade expected for this solution; if list, average grade for each subtask
`nbtests` | optional `int` | Number of test cases this solution is expected to be evaluated against

## default*

Any key name starting with "default" will be copied as-is to the `defaultParams.json` file. Please check [its documentation](defaultparams.md) for more information about these keys.

## overrideParams

* Name: `overrideParams`
* Type: `object`
* Example: `{"defaultFilterTests": [], "defaultDependencies-python2": "@defaultDependencies-python"}`

This key defines parameters to override in the generated [`defaultParams.json` file](defaultparams.md). The keys of this object will be copied as-is to the `defaultParams`, possibly overwriting automatically generated ones.
