"""Command line entry point: ``ltspice-run``."""

from __future__ import annotations

import argparse
from pathlib import Path

from ltspice_automation.raw import list_traces, raw_to_dataframe, read_raw, save_csv
from ltspice_automation.sim import run_sim


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ltspice-run",
        description="Run one LTspice schematic and print the path of the .raw file.",
    )
    parser.add_argument("schematic", type=Path, help="Path to a .asc schematic.")
    parser.add_argument(
        "--analysis",
        default=".tran 1m",
        help="Analysis directive, for example '.tran 1m' or '.dc V1 0 12 0.1'.",
    )
    parser.add_argument("--timeout", type=int, default=60, help="Seconds to wait for LTspice.")
    parser.add_argument("--output-dir", type=Path, help="Where to write .raw and .log files.")
    parser.add_argument("--csv", type=Path, help="Also write the traces to this CSV file.")
    parser.add_argument("--list-traces", action="store_true", help="Print the trace names.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raw_path = run_sim(
        args.schematic,
        analysis_card=args.analysis,
        output_dir=args.output_dir,
        wait_seconds=args.timeout,
    )
    print(raw_path)
    if args.list_traces:
        for name in list_traces(raw_path):
            print(name)
    if args.csv is not None:
        written = save_csv(raw_to_dataframe(read_raw(raw_path)), args.csv)
        print(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
