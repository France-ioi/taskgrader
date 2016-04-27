# Error messages

## Isolate is not properly installed

This error message happens when `isolate`, the tool used to isolate solution executions and gather metrics, was not properly installed. The taskgrader will fall back to a normal execution, which means the execution will not be isolated (allowing the solution to access the whole filesystem, or communicate over the network, for instance), and the taskgrader will not be able to tell how much time and memory the execution used. It's okay for a test environment, but `isolate` needs to be configured properly for a contest environment.

The script `install.sh` normally takes care of installing `isolate` properly; if not, try launching it again and looking for any error message related to `isolate`.

## Unable to import jsonschema

The taskgrader uses [jsonschema](https://github.com/Julian/jsonschema) for input and output JSON validation. It should normally be downloaded by the `install.sh` script, but it may fail if `git` is not installed. This validation is not mandatory, but if the input JSON is not valid, the taskgrader will most likely crash. The validation helps knowing which JSONs are invalid and why.

If `pip` is available, you can install jsonschema automatically with `pip install jsonschema`, alternatively you can download it manually from the [jsonschema GitHub repository](https://github.com/Julian/jsonschema).
