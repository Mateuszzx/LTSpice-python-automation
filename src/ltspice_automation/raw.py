"""Read LTspice ``.raw`` files into pandas tables and make a quick plot."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyLTSpice import LTSpiceLogReader, RawRead


def _ensure_path(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def _trace_names(raw: RawRead) -> List[str]:
    return list(raw.get_trace_names())


def _as_real(values: np.ndarray) -> np.ndarray:
    """Frequency and time are real sweep axes, even when the ``.raw`` stores them as complex."""
    values = np.asarray(values)
    if np.iscomplexobj(values):
        return np.real(values)
    return values


def _detect_axis(raw: RawRead, step: int = 0) -> Tuple[str, np.ndarray]:
    """Prefer ``time``, then ``frequency``, otherwise a generic ``x`` axis."""
    axis = _as_real(raw.get_axis(step))
    names = set(_trace_names(raw))

    if "time" in names:
        time_wave = _as_real(raw.get_trace("time").get_wave(step))
        if time_wave.shape == axis.shape:
            return "time", axis

    if "frequency" in names:
        frequency = _as_real(raw.get_trace("frequency").get_wave(step))
        if frequency.shape == axis.shape:
            return "frequency", axis

    return "x", axis


def _extract_wave(raw: RawRead, name: str, step: int = 0, complex_mode: str = "complex") -> np.ndarray:
    """Return one trace. AC data stays complex unless ``complex_mode`` says otherwise."""
    wave = np.asarray(raw.get_trace(name).get_wave(step))
    if not np.iscomplexobj(wave) or complex_mode == "complex":
        return wave
    if complex_mode == "magnitude":
        return np.abs(wave)
    if complex_mode == "real":
        return np.real(wave)
    if complex_mode == "imag":
        return np.imag(wave)
    raise ValueError("complex_mode must be 'complex', 'magnitude', 'real', or 'imag'")


def _choose_traces(
    names: set[str],
    *,
    prefer: Sequence[str] | None,
    include: Optional[Iterable[str]],
    skip: set[str],
) -> List[str]:
    if prefer is not None:
        chosen = [name for name in prefer if name in names]
        if include:
            chosen.extend(name for name in include if name in names and name not in chosen)
        if chosen:
            return chosen
        return [name for name in names if name not in skip][:2]
    return [name for name in names if name not in skip]


def list_traces(raw_path: Path | str) -> list[str]:
    """Return the trace names stored in a ``.raw`` file."""
    return _trace_names(RawRead(_ensure_path(raw_path)))


def read_raw(raw_path: Path | str) -> RawRead:
    """Open a ``.raw`` file and load every trace.

    PyLTSpice 6 reads only the header unless ``traces_to_read`` is set.
    The returned object also carries ``raw_filename`` so callers can find the
    matching ``.log``.
    """
    path = _ensure_path(raw_path)
    raw = RawRead(path, traces_to_read="*")
    raw.raw_filename = str(path)
    return raw


def raw_to_dataframe(
    raw: RawRead,
    *,
    step: int = 0,
    prefer: Sequence[str] | None = None,
    include: Optional[Iterable[str]] = None,
    complex_mode: str = "complex",
) -> pd.DataFrame:
    """Convert one step of a ``RawRead`` into a DataFrame.

    The first column is ``time``, ``frequency``, or ``x``, stored as real
    numbers. ``prefer`` names are kept first, then any extra names from
    ``include``. With neither argument, every trace except the x-axis is
    included. AC traces stay complex. Set ``complex_mode`` to ``magnitude``,
    ``real``, or ``imag`` to store a real projection instead.
    """
    names = set(_trace_names(raw))
    x_label, x_data = _detect_axis(raw, step)
    chosen = _choose_traces(names, prefer=prefer, include=include, skip={x_label})

    data: Dict[str, np.ndarray] = {x_label: x_data}
    for name in chosen:
        data[name] = _extract_wave(raw, name, step=step, complex_mode=complex_mode)
    return pd.DataFrame(data)


def _step_keys_from_log(log_path: Path, step_count: int) -> list[Any] | None:
    reader = LTSpiceLogReader(str(log_path))
    stepset = dict(getattr(reader, "stepset", {}) or {})
    if not stepset:
        return None

    names = list(stepset)
    width = len(next(iter(stepset.values())))
    if width != step_count:
        return None

    keys: list[Any] = []
    for index in range(width):
        values = [stepset[name][index] for name in names]
        keys.append(values[0] if len(names) == 1 else tuple(zip(names, values)))
    return keys


def raw_to_dataframes_by_step(
    raw: RawRead,
    *,
    prefer: Sequence[str] | None = None,
    include: Optional[Iterable[str]] = None,
    use_log_keys: bool = True,
    log_path: Optional[str] = None,
    complex_mode: str = "complex",
) -> dict[Any, pd.DataFrame]:
    """Convert a stepped ``.raw`` file into one DataFrame per step.

    When the matching ``.log`` lists ``.step`` values, those values are the
    dictionary keys. Otherwise the keys are the numeric step indexes.
    AC traces stay complex, same as ``raw_to_dataframe``.
    """
    names = set(_trace_names(raw))
    steps = list(raw.get_steps())
    skip = {"time", "frequency"}
    chosen = _choose_traces(names, prefer=prefer, include=include, skip=skip)

    step_keys: list[Any] = list(steps)
    if use_log_keys:
        inferred = Path(log_path) if log_path else Path(getattr(raw, "raw_filename", "")).with_suffix(".log")
        if inferred.is_file():
            try:
                keys = _step_keys_from_log(inferred, len(steps))
            except Exception:
                keys = None
            if keys is not None:
                step_keys = keys

    result: Dict[Any, pd.DataFrame] = {}
    for step, key in zip(steps, step_keys):
        x_label, x_data = _detect_axis(raw, step=step)
        data: Dict[str, np.ndarray] = {x_label: x_data}
        for name in chosen:
            data[name] = _extract_wave(raw, name, step=step, complex_mode=complex_mode)
        result[key] = pd.DataFrame(data)
    return result


def save_csv(df: pd.DataFrame, path: Path | str, *, index: bool = False) -> Path:
    """Write ``df`` to CSV, creating parent folders, and return the absolute path."""
    path = _ensure_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    return path


def quick_plot(df: pd.DataFrame, *, title: Optional[str] = None) -> None:
    """Plot the first signal against time, frequency, or the row index."""
    if df.empty:
        print("[quick_plot] Nothing to plot.")
        return

    x_col = "time" if "time" in df.columns else ("frequency" if "frequency" in df.columns else None)
    y_candidates = [column for column in df.columns if column != x_col] if x_col else list(df.columns)
    if not y_candidates:
        print("[quick_plot] No signal columns to plot.")
        return

    y_name = y_candidates[0]
    y_data = df[y_name].to_numpy()
    if np.iscomplexobj(y_data):
        y_plot = np.abs(y_data)
        y_label = f"|{y_name}|"
    else:
        y_plot = y_data
        y_label = y_name

    plt.figure()
    if x_col:
        plt.plot(df[x_col], y_plot, label=y_label)
        plt.xlabel("Time [s]" if x_col == "time" else "Frequency [Hz]")
    else:
        plt.plot(df.index, y_plot, label=y_label)
        plt.xlabel("Sample")

    plt.ylabel(y_label)
    plt.title(title or f"LTspice trace: {y_label}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
