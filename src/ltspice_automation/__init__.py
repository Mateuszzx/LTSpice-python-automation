"""Run LTspice from Python and turn ``.raw`` results into tables and plots."""

from ltspice_automation.paths import models_dir, project_root
from ltspice_automation.raw import (
    list_traces,
    quick_plot,
    raw_to_dataframe,
    raw_to_dataframes_by_step,
    read_raw,
    save_csv,
)
from ltspice_automation.sim import clear_sim_outputs, run_ac, run_dc, run_sim, run_tran

__version__ = "0.1.0"

__all__ = [
    "clear_sim_outputs",
    "list_traces",
    "models_dir",
    "project_root",
    "quick_plot",
    "raw_to_dataframe",
    "raw_to_dataframes_by_step",
    "read_raw",
    "run_ac",
    "run_dc",
    "run_sim",
    "run_tran",
    "save_csv",
]
