"""Run LTspice schematics and clean up the files a run leaves behind."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from PyLTSpice import LTspice, SimRunner, SpiceEditor


def ensure_analysis_card(spice: SpiceEditor, card: str) -> None:
    """Add an analysis directive such as ``.tran 1m`` or ``.dc V1 0 12 0.1``.

    LTspice ignores a repeated directive, so calling this more than once is safe.
    """
    spice.add_instructions(card)


def wait_for_raw(expected: Path, search_dir: Path, stem: str, timeout: int = 180) -> Path:
    """Poll until ``expected`` or the newest ``<stem>*.raw`` file appears."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if expected.exists():
            return expected

        candidates = list(search_dir.glob(f"{stem}*.raw"))
        if candidates:
            newest = max(candidates, key=lambda path: path.stat().st_mtime)
            if newest.exists():
                return newest
        time.sleep(0.25)

    raise TimeoutError(f"No .raw file for '{stem}' appeared in {search_dir} within {timeout}s.")


def _require_ltspice() -> None:
    if LTspice.is_available():
        return
    raise RuntimeError(
        "LTspice was not found. Install it, or point PyLTSpice at it with the "
        "LTSPICEFOLDER and LTSPICEEXECUTABLE environment variables. "
        "On Linux and macOS, Wine is used when those variables are unset."
    )


def run_sim(
    asc_path: Path | str,
    *,
    analysis_card: str = ".tran 1m",
    spice: SpiceEditor | None = None,
    output_dir: Optional[Path | str] = None,
    run_name: Optional[str] = None,
    wait_seconds: int = 60,
) -> Path:
    """Run one schematic and return the absolute path of the ``.raw`` file.

    Parameters
    ----------
    asc_path:
        LTspice schematic (``.asc``). Passing a netlist also works.
    analysis_card:
        Directive inserted before the run, for example ``.ac dec 100 1 1e6``.
    spice:
        Editor already configured by the caller. A new one is created when omitted.
    output_dir:
        Directory for ``.raw`` and ``.log``. Defaults to the schematic's folder.
    run_name:
        Output filename stem. Defaults to the schematic stem.
    wait_seconds:
        How long to wait for LTspice to finish.
    """
    asc_path = Path(asc_path).resolve()
    if not asc_path.exists():
        raise FileNotFoundError(f"Schematic not found: {asc_path}")

    _require_ltspice()

    if spice is None:
        spice = SpiceEditor(asc_path)
    ensure_analysis_card(spice, analysis_card)

    out_dir = Path(output_dir).resolve() if output_dir else asc_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    run_stem = run_name or asc_path.stem
    expected_raw = out_dir / f"{run_stem}.raw"

    runner = SimRunner(
        simulator=LTspice,
        parallel_sims=1,
        timeout=wait_seconds,
        verbose=False,
        output_folder=str(out_dir),
    )
    # Keep the .net suffix. A bare stem makes LTspice open the .asc instead,
    # which drops the analysis directive we just added.
    task = runner.run(spice, run_filename=f"{run_stem}.net", timeout=wait_seconds)
    if task is None:
        raise RuntimeError(f"LTspice did not start for {asc_path.name}.")

    if not runner.wait_completion(timeout=wait_seconds):
        log_path = out_dir / f"{run_stem}.log"
        detail = ""
        if log_path.exists():
            detail = log_path.read_text(errors="replace")[-2000:]
        raise RuntimeError(f"LTspice simulation failed or timed out for {asc_path.name}.\n{detail}".rstrip())

    if task.raw_file is not None and Path(task.raw_file).exists():
        return Path(task.raw_file).resolve()
    return wait_for_raw(expected_raw, out_dir, run_stem, timeout=wait_seconds).resolve()


def run_tran(asc: Path | str, tstop: str = "1m", **kwargs) -> Path:
    """Transient analysis. Example: ``run_tran('circuit.asc', tstop='5m')``."""
    return run_sim(asc, analysis_card=f".tran {tstop}", **kwargs)


def run_ac(
    asc: Path | str,
    dec: int = 200,
    fstart: float = 1.0,
    fstop: float = 1e6,
    **kwargs,
) -> Path:
    """AC analysis with a logarithmic sweep."""
    return run_sim(asc, analysis_card=f".ac dec {dec} {fstart:g} {fstop:g}", **kwargs)


def run_dc(
    asc: Path | str,
    source: str = "V1",
    start: float = 0.0,
    stop: float = 12.0,
    step: float = 0.1,
    **kwargs,
) -> Path:
    """DC sweep. Example: ``run_dc('circuit.asc', source='V1', start=0, stop=5, step=0.1)``."""
    return run_sim(asc, analysis_card=f".dc {source} {start:g} {stop:g} {step:g}", **kwargs)


def clear_sim_outputs(asc_path: Path | str) -> None:
    """Delete the usual LTspice products sitting next to a schematic.

    Removes ``.raw``, ``.log``, ``.op.raw``, ``.net``, ``.fails``, and a file
    with no extension that some LTspice versions write. Missing files are ignored.
    """
    asc_path = Path(asc_path).resolve()
    out_dir = asc_path.parent
    stem = asc_path.stem
    for path in (
        out_dir / f"{stem}.raw",
        out_dir / f"{stem}.log",
        out_dir / stem,
        out_dir / f"{stem}.net",
        out_dir / f"{stem}.op.raw",
        out_dir / f"{stem}.fails",
    ):
        if path.exists() and path.is_file():
            path.unlink()
