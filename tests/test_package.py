from pathlib import Path

import ltspice_automation
from ltspice_automation.paths import models_dir, project_root


def test_public_api_exports_the_notebook_helpers():
    for name in (
        "run_sim",
        "run_tran",
        "run_ac",
        "run_dc",
        "clear_sim_outputs",
        "read_raw",
        "list_traces",
        "raw_to_dataframe",
        "raw_to_dataframes_by_step",
        "save_csv",
        "quick_plot",
        "models_dir",
        "project_root",
    ):
        assert hasattr(ltspice_automation, name)


def test_models_dir_finds_the_shipped_schematics():
    root = project_root()
    ohm = models_dir("basic-components", "ohm_law", "ohm.asc")
    assert root == Path(__file__).resolve().parents[1]
    assert ohm.is_file()
    assert models_dir("operational-amplifier").is_dir()
    assert models_dir("transistors").is_dir()


def test_models_dir_rejects_a_missing_path():
    try:
        models_dir("does-not-exist")
    except FileNotFoundError as exc:
        assert "does-not-exist" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")
