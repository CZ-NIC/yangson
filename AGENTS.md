# Agent guidance

## Project layout

- `yangson/` contains the Python library and command-line entry points.
- `tests/` contains pytest tests.
- `yang-modules/` contains YANG modules and YANG Library fixtures used by tests.
- `docs/` contains the Sphinx documentation and examples.

## Code status

The input format of instance document can be either JSON/YAML or
XML. However, the XML part is undocumented and essentially unmaintained.

## Development

- Python support starts at 3.10; preserve that compatibility when changing library code.
- Use `uv sync --all-groups` to install development and documentation dependencies.
- Run the test suite with `make test` (`uv run --all-groups pytest tests`).
- The test suite modules use Python fixtures based on YANG modules from subdirectories of the `yang-modules` directory:
  * `test_model.py` from `test`
  * `test_c.py` from `testc`
  * `test_d.py` from `testd`.
  Any changes to those YANG modules should be reflected in the test modules.
- Run lint checks with `make lint` (`uv run ruff check .`).
- Keep changes focused and update tests or documentation when behavior or user-facing interfaces change.
