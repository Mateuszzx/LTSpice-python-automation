# ltspice_tools.py
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

# PyLTSpice editors and runner:
# - SpiceEditor edits/adds directives (.tran/.ac/.dc) and component values in .asc
# - SimRunner runs LTspice in batch and writes .raw/.log into output_folder
from PyLTSpice.editor.spice_editor import SpiceEditor
from PyLTSpice.sim.sim_runner import SimRunner


# ------------------------- Netlist helpers ------------------------- #

def ensure_analysis_card(spice: SpiceEditor, card: str) -> None:
    """
    Ensure an analysis directive (e.g., '.tran 1m', '.dc V1 0 12 0.1', '.ac dec 100 1 1e6')
    is present in the schematic via SpiceEditor.

    Notes:
      - SpiceEditor.add_instructions() is tolerant to duplicates (LTspice ignores repeated lines).
      - Keep this function minimal: caller decides which card to pass.
    """
    # Add the requested analysis instruction to the schematic/netlist.
    spice.add_instructions(card)


def wait_for_raw(expected: Path, search_dir: Path, stem: str, timeout: int = 180) -> Path:
    """
    Wait (poll) for the simulation .raw file to appear on disk.

    Strategy:
      1) Prefer an exact expected path (e.g., '<out>/<stem>.raw') if provided.
      2) Fallback to search_dir glob '{stem}*.raw' and pick the newest file.
      3) Poll until timeout is reached.

    Args:
      expected: The exact .raw path we anticipate (can be None-like, but here it's a Path).
      search_dir: Directory where LTspice writes results.
      stem: File stem for fallback matching (same as run_filename).
      timeout: Maximum seconds to wait.

    Returns:
      Path to the discovered .raw file.

    Raises:
      TimeoutError: If no matching .raw file is found before the timeout expires.
    """
    t0 = time.time()
    while time.time() - t0 < timeout:
        # Check the exact expected path first (fast path).
        if expected and expected.exists():
            return expected

        # Otherwise, look for any raw matching '<stem>*.raw' and pick the most recent one.
        cands = list(search_dir.glob(f"{stem}*.raw"))
        if cands:
            newest = max(cands, key=lambda p: p.stat().st_mtime)
            if newest.exists():
                return newest

        # Small sleep to avoid busy-waiting.
        time.sleep(0.25)

    # Nothing found within timeout window.
    raise TimeoutError("Plik .raw nie został wygenerowany w czasie oczekiwania.")


# --------------------------- Simulation ---------------------------- #

def run_sim(
    asc_path: Path | str,
    *,
    analysis_card: str = ".tran 1m",
    spice: SpiceEditor | None = None,
    output_dir: Optional[Path | str] = None,
    run_name: Optional[str] = None,
    wait_seconds: int = 30,
) -> Path:
    """
    Run an LTspice simulation for a given schematic and return the produced .raw path.

    Parameters
    ----------
    asc_path : Path | str
        Path to the LTspice schematic (.asc).
    analysis_card : str
        Analysis directive to ensure (e.g., '.tran 1m', '.ac dec 100 1 1e6', '.dc V1 0 12 0.1').
    spice : SpiceEditor | None
        Optional pre-configured SpiceEditor instance. If None, one is created from asc_path.
    output_dir : Optional[Path | str]
        Directory for .raw/.log outputs. Defaults to the .asc directory.
    run_name : Optional[str]
        Stem for output filenames. Defaults to asc_path.stem (i.e., schematic name).
    wait_seconds : int
        Timeout passed to runner and file polling (seconds).

    Returns
    -------
    Path
        Absolute path to the resulting .raw file.

    Raises
    ------
    FileNotFoundError
        If the provided asc_path does not exist.
    TimeoutError
        If the .raw file is not produced within wait_seconds.
    """
    # Normalize and validate schematic path.
    asc_path = Path(asc_path).resolve()
    if not asc_path.exists():
        raise FileNotFoundError(f"ASC file not found: {asc_path}")

    # Create a SpiceEditor if the caller didn't pass one.
    if spice is None:
        spice = SpiceEditor(str(asc_path))

    # Make sure the requested analysis directive is present in the schematic.
    ensure_analysis_card(spice, analysis_card)

    # Determine the output directory; default to schematic folder.
    out_dir = Path(output_dir).resolve() if output_dir else asc_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine base name used for output files.
    run_stem = run_name or asc_path.stem
    # Path we expect LTspice to write (common case).
    raw_path = out_dir / f"{run_stem}.raw"

    # Create a runner bound to the output folder.
    # If you need to force a specific LTspice.exe, pass ltspice_exe=...
    runner = SimRunner(output_folder=str(out_dir))

    # Launch the simulation (non-blocking in some versions).
    runner.run(spice, run_filename=run_stem, timeout=wait_seconds)

    # Wait (poll) until the .raw appears or timeout expires.
    return wait_for_raw(raw_path, out_dir, run_stem, timeout=wait_seconds).resolve()


def run_tran(asc: Path | str, tstop: str = "1m", **kw) -> Path:
    """
    Convenience wrapper for transient analysis (.tran).
    Example: run_tran('circuit.asc', tstop='5m')
    """
    return run_sim(asc, analysis_card=f".tran {tstop}", **kw)


def run_ac(asc: Path | str, dec: int = 200, fstart: float = 1.0, fstop: float = 1e6, **kw) -> Path:
    """
    Convenience wrapper for AC analysis (log sweep).
    Example: run_ac('circuit.asc', dec=100, fstart=10, fstop=1e6)
    """
    return run_sim(asc, analysis_card=f".ac dec {dec} {fstart:g} {fstop:g}", **kw)


def run_dc(asc: Path | str, source: str = "V1", start: float = 0.0, stop: float = 12.0, step: float = 0.1, **kw) -> Path:
    """
    Convenience wrapper for DC sweep.
    Example: run_dc('circuit.asc', source='V1', start=0, stop=5, step=0.1)
    """
    return run_sim(asc, analysis_card=f".dc {source} {start:g} {stop:g} {step:g}", **kw)


def clear_sim_outputs(asc_path: Path | str) -> None:
    """
    Delete common LTspice outputs for a given .asc schematic.

    Removes (if present):
      - <stem>.raw
      - <stem>.log
      - <stem>         (some LTspice versions create an output without extension)
      - <stem>.op.raw
      - <stem>.fails

    Notes:
      - This is a best-effort cleanup (ignores missing files).
      - Paths are derived from asc_path's folder and stem.

    Parameters
    ----------
    asc_path : Path | str
        Path to the LTspice schematic (.asc).
    """
    # Resolve schematic path and output directory.
    asc_path = Path(asc_path).resolve()
    out_dir = asc_path.parent
    run_stem = asc_path.stem

    # Common artifacts produced by LTspice.
    raw_path = out_dir / f"{run_stem}.raw"
    log_path = out_dir / f"{run_stem}.log"
    norm_path = out_dir / f"{run_stem}"          # sometimes a file (no extension) appears
    # net_path = out_dir / f"{run_stem}.net"     # intentionally not removed
    op_path = out_dir / f"{run_stem}.op.raw"
    fails_path = out_dir / f"{run_stem}.fails"

    # Remove files if they exist (ignore errors).
    for path in (raw_path, log_path, norm_path, fails_path, op_path):
        if path.exists():
            path.unlink()