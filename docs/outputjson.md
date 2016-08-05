# Output JSON

This page describes the *output JSON*, which is the JSON data returned by the taskgrader (on its standard output) after a successful evaluation.

This page is currently under writing, but you can check the output JSON format in the file `schema_output.json`.

### Exit sig values

These are the values for the field `exitSig` in any execution report from the output JSON. If > 0, means the execution was killed by a signal.

| Value | Meaning |
| ----- | ------- |
| -1 | Exit signal unknown (execution outside isolate for instance) |
| 0 | No exit signal sent to the program, it exited by itself |
| 6 | Abort signal |
| 7 | Bus error |
| 8 | Floating point exception |
| 11 | Segmentation fault |
| 137 | Execution timed out |
