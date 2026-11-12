import shutil

import numpy as np
import pytest
from PyLTSpice import LTspice

from ltspice_automation.paths import models_dir
from ltspice_automation.raw import list_traces, raw_to_dataframe, read_raw
from ltspice_automation.sim import clear_sim_outputs, run_sim, run_tran

pytestmark = pytest.mark.skipif(
    not LTspice.is_available(),
    reason="LTspice is not installed (on Linux/macOS it is used through Wine).",
)


def test_ohm_law_transient_writes_a_raw_file(tmp_path):
    source = models_dir("basic-components", "ohm_law", "ohm.asc")
    schematic = tmp_path / source.name
    shutil.copy(source, schematic)

    raw_path = run_tran(schematic, tstop="1m", output_dir=tmp_path, wait_seconds=180)

    assert raw_path.is_file()
    names = list_traces(raw_path)
    assert "time" in names
    frame = raw_to_dataframe(read_raw(raw_path))
    assert "time" in frame.columns
    assert len(frame) > 2
    assert frame["time"].max() >= 0.9e-3

    clear_sim_outputs(schematic)
    assert not raw_path.exists()


def test_ac_analysis_keeps_complex_traces(tmp_path):
    source = models_dir("basic-components", "ohm_law", "ohm.asc")
    schematic = tmp_path / source.name
    shutil.copy(source, schematic)

    raw_path = run_sim(
        schematic,
        analysis_card=".ac dec 10 1 1e6",
        output_dir=tmp_path,
        wait_seconds=180,
    )
    frame = raw_to_dataframe(read_raw(raw_path))

    assert np.isrealobj(frame["frequency"].to_numpy())
    signals = [column for column in frame.columns if column != "frequency"]
    assert signals
    assert np.iscomplexobj(frame[signals[0]].to_numpy())
