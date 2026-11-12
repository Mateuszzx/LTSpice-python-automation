# LTSpice Python Automation

A small installable package for running LTspice from Python, reading `.raw` results into pandas, and exploring the included schematics from Jupyter.

The library code lives in `src/ltspice_automation`. Example circuits live in `models/`. The notebooks import the installed package, so they work after `uv sync` without adding folders to `sys.path`.

## Requirements

- Python 3.11 or newer (this checkout uses 3.14, pinned in `.python-version`)
- [uv](https://docs.astral.sh/uv/)
- LTspice
  - Windows: a normal LTspice install
  - Linux and macOS: LTspice under Wine. PyLTSpice finds the usual Wine path on its own. To point at a different install, set `LTSPICEFOLDER` and `LTSPICEEXECUTABLE`.

## Setup

```bash
uv sync
```

That creates `.venv`, installs this project in editable mode, and installs Jupyter with the development tools.

Run a schematic from the command line:

```bash
uv run ltspice-run models/basic-components/ohm_law/ohm.asc --analysis ".tran 1m" --list-traces
```

Open the notebooks with the same environment:

```bash
uv run jupyter lab notebooks
```

In Cursor or VS Code, pick the `.venv` interpreter for the notebook kernel. The first cell of each notebook imports `ltspice_automation` and locates schematics with `models_dir()`, so the kernel's working directory does not matter.

## Using the package

```python
from ltspice_automation import run_tran, read_raw, raw_to_dataframe, models_dir

schematic = models_dir("basic-components", "ohm_law", "ohm.asc")
raw_path = run_tran(schematic, tstop="1m")
frame = raw_to_dataframe(read_raw(raw_path))
```

`run_ac` and `run_dc` cover the other two analysis types. `raw_to_dataframes_by_step` splits a `.step` result into one table per step.

## Layout

- `src/ltspice_automation/` — simulation runner, `.raw` reader, and path helpers
- `models/` — example `.asc` schematics
- `notebooks/` — basic components, operational amplifiers, and transistors
- `tests/` — import checks and one real LTspice run when the simulator is installed

## Tests

```bash
uv run pytest
```
