# LTSpice Python Automation

Automate LTspice simulations from Python, parse results, and explore circuits via notebooks and scripts.

> **Status:** This repo is a small collection of **easy scripts and minimal notebooks** showing how to use the **[PyLTSpice](https://pypi.org/project/PyLTSpice/)** library with LTspice. It’s meant as a learning/boilerplate starting point. If new needs come up, more features may be added later.

## Features

- Run LTspice in batch/headless mode from Python
- Parse `.raw` / `.log` into NumPy / Pandas
- Tiny parameter sweeps, quick plots, and short reports
- Reusable utility snippets for new workflows
- Simple, readable Jupyter notebooks

## What’s in this repo?

- `scripts/` — small, self-contained examples (run & parse)
- `notebooks/` — simple, step-by-step demos
- `ltspice_tools.py` — lightweight helpers around PyLTSpice
- `examples/` — example `.asc` / netlists for testing

## Requirements

- Windows with **LTspice installed** (recommended)
- Python **3.9+**
- **PyLTSpice** and common PyData packages

## Install

```bash
git clone https://github.com/Mateuszzx/LTSpice-python-automation.git
cd LTSpice-python-automation

python -m venv .venv
# Windows
. .venv/Scripts/activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
