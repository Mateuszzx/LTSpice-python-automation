from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Iterable, Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# PyLTSpice RAW reader (new API)
from PyLTSpice import RawRead


# ----------------------------- Helpers ----------------------------- #

def _ensure_path(p: Path | str) -> Path:
    """
    Normalize any input path (str/Path) to an absolute Path.
    """
    return Path(p).expanduser().resolve()


def _trace_names(rr: RawRead) -> List[str]:
    """
    Return all trace names provided by the RawRead object.
    """
    return list(rr.get_trace_names())


def _detect_axis(rr: RawRead, step: int = 0) -> Tuple[str, np.ndarray]:
    """
    Detect and return the best x-axis label and data for the given step.

    Order of preference:
    - 'time' if present and shape matches the axis
    - 'frequency' if present and shape matches the axis
    - generic axis 'x'
    """
    axis = rr.get_axis(step)
    names = set(_trace_names(rr))

    # Prefer time
    if "time" in names:
        t = rr.get_trace("time").get_wave(step)
        if t.shape == axis.shape:
            return "time", np.asarray(axis)

    # Then frequency (AC analysis)
    if "frequency" in names:
        f = rr.get_trace("frequency").get_wave(step)
        if f.shape == axis.shape:
            return "frequency", np.asarray(axis)

    # Fallback generic x-axis
    return "x", np.asarray(axis)


def _extract_wave(rr: RawRead, name: str, step: int = 0, complex_mode: str = "magnitude") -> np.ndarray:
    """
    Return a numpy array for the given trace, handling complex data if needed.

    complex_mode:
      - 'magnitude': use np.abs() for complex traces
      - 'real':      use np.real()
      - 'imag':      use np.imag()
    """
    wave = rr.get_trace(name).get_wave(step)
    arr = np.asarray(wave)

    if np.iscomplexobj(arr):
        if complex_mode == "real":
            return np.real(arr)
        if complex_mode == "imag":
            return np.imag(arr)
        # default to magnitude
        return np.abs(arr)

    return arr


# ----------------------------- RAW I/O ----------------------------- #

def list_traces(raw_path: Path | str) -> list[str]:
    """
    Open a .raw file (PyLTSpice) and return available trace names.

    Example:
        list_traces("path/to/sim.raw") -> ["time", "V(n001)", "I(R1)", ...]
    """
    rr = RawRead(str(_ensure_path(raw_path)))
    return _trace_names(rr)


def read_raw(raw_path: Path | str) -> RawRead:
    """
    Open a .raw file and return a RawRead handle.

    Example:
        rr = read_raw("path/to/sim.raw")
        rr.get_trace("V(n001)").get_wave(0)  # numpy array
    """
    return RawRead(str(_ensure_path(raw_path)))


def raw_to_dataframe(
    rr: RawRead,
    *,
    step: int = 0,
    prefer: Sequence[str] | None = None,
    include: Optional[Iterable[str]] = None,
    complex_mode: str = "magnitude",
) -> pd.DataFrame:
    """
    Convert RawRead traces to a tidy DataFrame for a single step.

    Columns:
      - x-axis: 'time' (transient), 'frequency' (AC), or 'x' (fallback)
      - selected signal columns (see selection rules below)

    Selection rules:
      - If 'prefer' is provided, keep those names in order if they exist.
      - Then append unique names from 'include' if provided.
      - If nothing specified, take all traces except the x-axis candidate.

    Args:
      rr: RawRead instance
      step: index of the step to extract (0-based)
      prefer: prioritized names to include first
      include: additional names to include
      complex_mode: 'magnitude' | 'real' | 'imag' for complex traces

    Returns:
      DataFrame with x-axis + selected traces.
    """
    names = set(_trace_names(rr))
    x_label, x_data = _detect_axis(rr, step)

    # Build trace selection
    if prefer is not None:
        chosen: List[str] = [n for n in prefer if n in names]
        if include:
            chosen.extend([n for n in include if n in names and n not in chosen])
        if not chosen:
            chosen = [n for n in names if n != x_label][:2]
    else:
        chosen = [n for n in names if n != x_label]

    data: Dict[str, np.ndarray] = {x_label: x_data}
    for n in chosen:
        data[n] = _extract_wave(rr, n, step=step, complex_mode=complex_mode)

    return pd.DataFrame(data)


def raw_to_dataframes_by_step(
    rr: RawRead,
    *,
    prefer: Sequence[str] | None = None,
    include: Optional[Iterable[str]] = None,
    use_log_keys: bool = True,
    log_path: Optional[str] = None,
    complex_mode: str = "magnitude",
) -> dict[Any, pd.DataFrame]:
    """
    Convert a stepped RAW into a dict of DataFrame per step.

    Keys:
      - If use_log_keys=True and the .log is available, keys will be the stepped values
        (e.g., a voltage or parameter value per step). Otherwise numeric indices.

    Columns per DataFrame:
      - x-axis: 'time', 'frequency', or 'x'
      - selected signal columns (see raw_to_dataframe selection rules)

    Args:
      rr: RawRead instance
      prefer/include: same selection rules as raw_to_dataframe
      use_log_keys: try to decode step variable values from the .log
      log_path: optional custom path to .log; if None, infer from RAW filename
      complex_mode: 'magnitude' | 'real' | 'imag' for complex traces

    Returns:
      dict[key, DataFrame]
    """
    names = set(_trace_names(rr))
    steps = rr.get_steps()  # e.g., [0, 1, 2, ...]

    # Choose signals once (applied to all steps)
    if prefer is not None:
        chosen: List[str] = [p for p in prefer if p in names]
        if include:
            chosen.extend([n for n in include if n in names and n not in chosen])
        if not chosen:
            chosen = [n for n in names if n.lower() not in ("time", "frequency")][:2]
    else:
        chosen = [n for n in names if n.lower() not in ("time", "frequency")]

    # Try to build human-friendly keys from the .log file
    step_keys: List[Any] = list(steps)
    if use_log_keys:
        try:
            # Prefer new path; fallback to older API if needed
            try:
                from PyLTSpice.log.ltsteps import LTSpiceLogReader  # new path
            except Exception:
                from PyLTSpice.LTSteps import LTSpiceLogReader      # old path

            log_reader = LTSpiceLogReader(log_path) if log_path else LTSpiceLogReader(rr.raw_filename.replace(".raw", ".log"))
            vars_ = log_reader.get_step_vars()  # list of variable names stepped
            keys: List[Any] = []
            for i in range(log_reader.step_count):
                vals = [log_reader[v][i] for v in vars_]
                if len(vars_) == 1:
                    keys.append(vals[0])
                else:
                    keys.append(tuple((v, vals[j]) for j, v in enumerate(vars_)))
            if len(keys) == len(steps):
                step_keys = keys
        except Exception:
            # If log parsing fails, keep numeric indices
            pass

    result: Dict[Any, pd.DataFrame] = {}
    for s, key in zip(steps, step_keys):
        x_label, x_data = _detect_axis(rr, step=s)
        data: Dict[str, np.ndarray] = {x_label: x_data}
        for n in chosen:
            data[n] = _extract_wave(rr, n, step=s, complex_mode=complex_mode)
        result[key] = pd.DataFrame(data)

    return result


def save_csv(df: pd.DataFrame, path: Path | str, *, index: bool = False) -> Path:
    """
    Save a DataFrame to CSV and return the absolute path.
    Creates parent folders if necessary.
    """
    path = _ensure_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    return path


# ---------------------------- Plotting ----------------------------- #

def quick_plot(df: pd.DataFrame, *, title: Optional[str] = None) -> None:
    """
    Quick-look plot:
      - If 'time' column exists, plot first non-time signal vs time.
      - Else if 'frequency', plot first non-frequency signal vs frequency.
      - Else plot first column vs index.

    This avoids heavy styling so you can theme elsewhere.
    """
    if df.empty:
        print("[quick_plot] Nothing to plot.")
        return

    # Prefer time, then frequency
    x_col = "time" if "time" in df.columns else ("frequency" if "frequency" in df.columns else None)
    y_candidates = [c for c in df.columns if c != x_col] if x_col else list(df.columns)

    if not y_candidates:
        print("[quick_plot] No signal columns to plot.")
        return

    y = y_candidates[0]
    y_data = df[y].to_numpy()

    # For complex data, plot magnitude
    if np.iscomplexobj(y_data):
        y_plot = np.abs(y_data)
        y_label = f"|{y}|"
    else:
        y_plot = y_data
        y_label = y

    plt.figure()
    if x_col:
        plt.plot(df[x_col], y_plot, label=y_label)
        plt.xlabel("Time [s]" if x_col == "time" else "Frequency [Hz]")
    else:
        plt.plot(df.index, y_plot, label=y_label)
        plt.xlabel("Sample")

    plt.ylabel(y_label)
    plt.title(title or f"LTspice Trace: {y_label}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()