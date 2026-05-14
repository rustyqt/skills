#!/usr/bin/env python3
"""CLI tool for querying FPGA simulation waveform data.

Converts QuestaSim WLF files to VCD on demand, then queries signal values,
transitions, edges, and state machine behaviour from the command line.

Requires: pip install vcdvcd

Usage:
    python sim/wavequery.py --test "*boot*fail*" list-signals --filter "*dut*"
    python sim/wavequery.py --test "*boot*" value-at --signal "*state*" --time 500ns
    python sim/wavequery.py --test "*boot*" transitions --signal "*state*"
    python sim/wavequery.py --help
"""

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Find the repo root. Walk up from CWD first (which is the common case when
# wavequery.py is invoked from inside a checked-out repo even though the script
# itself lives in a skills folder outside the repo). Fall back to the script
# dir if CWD doesn't yield a hit.
def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / "sim" / "run.py").exists() or (cur / "run.py").exists():
            return cur
        cur = cur.parent
    return start  # nothing useful — leave CWD as the default

_repo_root = _find_repo_root(Path.cwd())
if not (_repo_root / "sim" / "run.py").exists() and not (_repo_root / "run.py").exists():
    _repo_root = _find_repo_root(Path(__file__).resolve().parent)

try:
    from vcdvcd import VCDVCD
except ImportError:
    print("Error: vcdvcd is required. Install with: python -m pip install vcdvcd",
          file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

_TIME_UNITS = {
    "ps": 1,
    "ns": 1_000,
    "us": 1_000_000,
    "ms": 1_000_000_000,
    "s":  1_000_000_000_000,
}

_TIME_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*(ps|ns|us|ms|s)?\s*$")


def parse_time(s):
    """Parse a human-readable time string to picoseconds (int).

    Accepts: '500ns', '1.5us', '10ms', '200' (plain int = ps).
    """
    m = _TIME_RE.match(s)
    if not m:
        raise ValueError(f"Invalid time format: '{s}'")
    value = float(m.group(1))
    unit = m.group(2) or "ps"
    return int(value * _TIME_UNITS[unit])


def format_time(ps):
    """Format picoseconds into a human-readable string."""
    if ps == 0:
        return "0 ps"
    for unit in ["s", "ms", "us", "ns", "ps"]:
        factor = _TIME_UNITS[unit]
        if ps >= factor and ps % factor == 0:
            val = ps // factor
            return f"{val} {unit}"
    # Non-exact — use the largest unit that fits
    for unit in ["ms", "us", "ns"]:
        factor = _TIME_UNITS[unit]
        if ps >= factor:
            val = ps / factor
            if val == int(val):
                return f"{int(val)} {unit}"
            return f"{val:.3g} {unit}"
    return f"{ps} ps"


# ---------------------------------------------------------------------------
# Value formatting
# ---------------------------------------------------------------------------

def format_value_hex(binstr):
    """Convert a binary string (e.g. '0010') to hex. Returns 'x' for metavalues."""
    if any(c in binstr for c in "xXzZuU-"):
        return binstr
    try:
        n = int(binstr, 2)
        width = (len(binstr) + 3) // 4  # hex digits needed
        return f"0x{n:0{width}x}"
    except ValueError:
        return binstr


# ---------------------------------------------------------------------------
# WLF to VCD converter
# ---------------------------------------------------------------------------

class WlfToVcdConverter:
    """Converts QuestaSim WLF files to VCD using wlf2vcd."""

    def __init__(self):
        self._wlf2vcd = self._find_wlf2vcd()

    @staticmethod
    def _find_wlf2vcd():
        """Auto-discover wlf2vcd on PATH.

        Ships with QuestaSim / ModelSim. Open Logic does not bundle it — the user
        needs Questa installed and its `bin/` directory on PATH for WLF support.
        """
        return shutil.which("wlf2vcd")

    def convert(self, wlf_path):
        """Convert a WLF file to VCD. Returns path to the VCD file.

        Caches the VCD alongside the WLF; skips conversion if VCD is newer.
        """
        wlf_path = Path(wlf_path)
        vcd_path = wlf_path.with_suffix(".vcd")

        if vcd_path.exists() and vcd_path.stat().st_mtime > wlf_path.stat().st_mtime:
            return str(vcd_path)

        if not self._wlf2vcd:
            raise RuntimeError(
                "wlf2vcd not found on PATH. WLF inputs require QuestaSim/ModelSim "
                "to be installed and its bin/ directory on PATH. For GHDL or NVC, "
                "re-run the simulation with `--gtkwave-fmt vcd` and point wavequery "
                "at the resulting .vcd file directly."
            )

        cmd = [self._wlf2vcd, "-o", str(vcd_path), str(wlf_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"wlf2vcd failed:\n{result.stderr}")

        return str(vcd_path)


# ---------------------------------------------------------------------------
# Test finder
# ---------------------------------------------------------------------------

class TestFinder:
    """Resolves VUnit test output directories.

    VUnit writes waveform files under simulator-specific subfolders inside
    each test-output directory:

        <vunit_out>/test_output/<lib>.<tb>.<config>_<hash>/
            ghdl/wave.vcd          ← GHDL (--gtkwave-fmt vcd)
            ghdl/wave.ghw          ← GHDL (--gtkwave-fmt ghw)
            nvc/wave.fst           ← NVC  (--gtkwave-fmt fst)
            nvc/wave.vcd           ← NVC  (--gtkwave-fmt vcd)
            modelsim/vsim.wlf      ← Questa/ModelSim (default)
            modelsim/vsim.vcd      ← Questa/ModelSim (after wlf2vcd conversion)
    """

    # (subdir, filename, kind)
    _WAVE_LOCATIONS = (
        ("ghdl",     "wave.vcd",  "vcd"),
        ("nvc",      "wave.vcd",  "vcd"),
        ("modelsim", "vsim.vcd",  "vcd"),
        ("modelsim", "vsim.wlf",  "wlf"),
    )

    def __init__(self, vunit_out):
        self._test_output = Path(vunit_out) / "test_output"

    @classmethod
    def _wave_files(cls, test_dir):
        """Return list of (path, kind) for every wave file present in a test dir."""
        return [
            (test_dir / sub / fname, kind)
            for sub, fname, kind in cls._WAVE_LOCATIONS
            if (test_dir / sub / fname).exists()
        ]

    def list_tests(self, pattern=None):
        """List test directories, optionally filtered by glob pattern.

        Returns list of (test_name, test_dir, has_wlf, has_vcd).
        """
        if not self._test_output.exists():
            return []
        results = []
        for d in sorted(self._test_output.iterdir()):
            if not d.is_dir():
                continue
            name = d.name
            if pattern and not fnmatch.fnmatch(name, pattern):
                continue
            files = self._wave_files(d)
            has_vcd = any(kind == "vcd" for _, kind in files)
            has_wlf = any(kind == "wlf" for _, kind in files)
            results.append((name, str(d), has_wlf, has_vcd))
        return results

    def find_test_dir(self, pattern):
        """Find a single test directory matching the pattern.

        Raises if zero or multiple matches.
        """
        matches = self.list_tests(pattern)
        if not matches:
            raise FileNotFoundError(f"No test matching '{pattern}' found in {self._test_output}")
        if len(matches) > 1:
            names = "\n  ".join(m[0] for m in matches)
            raise ValueError(
                f"Multiple tests match '{pattern}'. Be more specific:\n  {names}"
            )
        return matches[0]

    def get_wlf_path(self, test_dir):
        """Return the WLF path if present, else None."""
        for path, kind in self._wave_files(Path(test_dir)):
            if kind == "wlf":
                return path
        return None

    def get_vcd_path(self, test_dir):
        """Return the first VCD path found across known simulator subdirs, else None."""
        for path, kind in self._wave_files(Path(test_dir)):
            if kind == "vcd":
                return path
        return None


# ---------------------------------------------------------------------------
# VCD query engine
# ---------------------------------------------------------------------------

class VcdQueryEngine:
    """Wraps vcdvcd for structured signal queries."""

    def __init__(self, vcd_path):
        self._path = vcd_path
        self._sig_list_cache = None

    def _load(self, signals=None, only_sigs=False, to_time=None):
        """Parse VCD with optional filters. Returns a new VCDVCD instance."""
        kwargs = {"vcd_path": self._path}
        if signals:
            kwargs["signals"] = signals
        if only_sigs:
            kwargs["only_sigs"] = True
        if to_time is not None:
            kwargs["to_time"] = to_time
        return VCDVCD(**kwargs)

    def _load_sig_list(self):
        """Load and cache the signal name list (header-only parse)."""
        if self._sig_list_cache is None:
            self._sig_list_cache = self._load(only_sigs=True)
        return self._sig_list_cache

    def list_signals(self, filter_pattern=None):
        """List all signals. Returns list of (name, width, var_type)."""
        vcd = self._load_sig_list()
        results = []
        for sig_name in vcd.signals:
            if filter_pattern and not fnmatch.fnmatch(sig_name.lower(), filter_pattern.lower()):
                continue
            sig_id = vcd.references_to_ids.get(sig_name)
            if sig_id and sig_id in vcd.data:
                sig = vcd.data[sig_id]
                results.append((sig_name, sig.size, sig.var_type))
            else:
                results.append((sig_name, "?", "?"))
        return results

    def _resolve_signal(self, pattern):
        """Resolve a signal pattern to its exact name. Supports glob."""
        vcd = self._load_sig_list()
        if pattern in vcd.references_to_ids:
            return pattern
        # Try glob matching
        matches = [s for s in vcd.signals if fnmatch.fnmatch(s.lower(), pattern.lower())]
        if not matches:
            raise ValueError(f"No signal matching '{pattern}'")
        if len(matches) > 1:
            listing = "\n  ".join(matches[:20])
            extra = f"\n  ... and {len(matches) - 20} more" if len(matches) > 20 else ""
            raise ValueError(f"Multiple signals match '{pattern}'. Be more specific:\n  {listing}{extra}")
        return matches[0]

    def value_at(self, signal_pattern, times_ps):
        """Get signal value at one or more times.

        Returns list of (time_ps, signal_name, value_bin).
        """
        sig_name = self._resolve_signal(signal_pattern)
        max_time = max(times_ps) if times_ps else None
        vcd = self._load(signals=[sig_name], to_time=max_time)
        sig = vcd[sig_name]
        results = []
        for t in times_ps:
            val = sig[t]
            results.append((t, sig_name, val))
        return results

    def transitions(self, signal_pattern, from_ps=None, to_ps=None):
        """Get all transitions of a signal in a time range.

        Returns list of (time_ps, value_bin).
        """
        sig_name = self._resolve_signal(signal_pattern)
        vcd = self._load(signals=[sig_name], to_time=to_ps)
        sig = vcd[sig_name]
        results = []
        for t, v in sig.tv:
            if from_ps is not None and t < from_ps:
                continue
            if to_ps is not None and t > to_ps:
                break
            results.append((t, v))
        return sig_name, results

    def find_edge(self, signal_pattern, edge_type="rising", nth=1):
        """Find the Nth rising or falling edge of a signal.

        Returns (time_ps, value_before, value_after) or None.
        """
        sig_name = self._resolve_signal(signal_pattern)
        vcd = self._load(signals=[sig_name])
        sig = vcd[sig_name]
        count = 0
        prev_val = None
        for t, v in sig.tv:
            if prev_val is not None:
                is_rising = prev_val == "0" and v == "1"
                is_falling = prev_val == "1" and v == "0"
                if (edge_type == "rising" and is_rising) or \
                   (edge_type == "falling" and is_falling) or \
                   (edge_type == "any" and (is_rising or is_falling)):
                    count += 1
                    if count == nth:
                        return sig_name, t, prev_val, v
            prev_val = v
        return sig_name, None, None, None

    def duration(self, signal_pattern, value, after_ps=0):
        """Find how long a signal holds a given value (first occurrence after after_ps).

        Returns (signal_name, start_ps, end_ps, duration_ps) or None values.
        """
        sig_name = self._resolve_signal(signal_pattern)
        vcd = self._load(signals=[sig_name])
        sig = vcd[sig_name]
        start = None
        for i, (t, v) in enumerate(sig.tv):
            if t < after_ps:
                continue
            if v == value and start is None:
                start = t
            elif v != value and start is not None:
                return sig_name, start, t, t - start
        # Signal held value until end of simulation
        if start is not None:
            return sig_name, start, vcd.endtime, vcd.endtime - start
        return sig_name, None, None, None

    def compare(self, signal_pattern, expect_pairs):
        """Compare expected vs actual values at given times.

        expect_pairs: list of (time_ps, expected_value_bin)
        Returns list of (time_ps, expected, actual, match_bool).
        """
        sig_name = self._resolve_signal(signal_pattern)
        max_time = max(t for t, _ in expect_pairs) if expect_pairs else None
        vcd = self._load(signals=[sig_name], to_time=max_time)
        sig = vcd[sig_name]
        results = []
        for t, expected in expect_pairs:
            actual = sig[t]
            # Width-aware comparison: convert both to int for numeric equality
            try:
                match = int(actual, 2) == int(expected, 2)
            except ValueError:
                match = actual == expected
            results.append((t, expected, actual, match))
        return sig_name, results

    def fsm(self, signal_pattern, state_names=None):
        """Trace state machine transitions with optional named states.

        state_names: dict mapping value -> name (e.g. {'0001': 'IDLE'})
        Returns list of (time_ps, value, name, duration_ps).
        """
        sig_name = self._resolve_signal(signal_pattern)
        vcd = self._load(signals=[sig_name])
        sig = vcd[sig_name]
        if not state_names:
            state_names = {}
        results = []
        for i, (t, v) in enumerate(sig.tv):
            name = state_names.get(v, v)
            if i + 1 < len(sig.tv):
                dur = sig.tv[i + 1][0] - t
            else:
                dur = vcd.endtime - t
            results.append((t, v, name, dur))
        return sig_name, results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_table(headers, rows, file=sys.stdout):
    """Print aligned text table."""
    if not rows:
        print("(no results)", file=file)
        return
    # Compute column widths
    all_rows = [headers] + [[str(c) for c in r] for r in rows]
    widths = [max(len(r[i]) for r in all_rows) for i in range(len(headers))]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers), file=file)
    print(fmt.format(*["-" * w for w in widths]), file=file)
    for r in all_rows[1:]:
        print(fmt.format(*r), file=file)


def print_json(data, file=sys.stdout):
    """Print JSON output."""
    json.dump(data, file, indent=2)
    print(file=file)


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def resolve_vcd(args, converter, finder):
    """Resolve the VCD file from --vcd, --wlf, or --test args."""
    if args.vcd:
        return args.vcd
    if args.wlf:
        return converter.convert(args.wlf)
    if args.test:
        _, test_dir, has_wlf, has_vcd = finder.find_test_dir(args.test)
        vcd_path = finder.get_vcd_path(test_dir)
        if has_vcd:
            return str(vcd_path)
        wlf_path = finder.get_wlf_path(test_dir)
        if has_wlf:
            return converter.convert(str(wlf_path))
        raise FileNotFoundError(
            f"No WLF or VCD file found for test. "
            f"Re-run with waveform capture: python sim/run.py -v \"{args.test}\" --gtkwave-fmt vcd"
        )
    raise ValueError("Specify --test, --vcd, or --wlf to select a waveform source.")


def cmd_list_tests(args, finder):
    tests = finder.list_tests(args.pattern)
    if args.format == "json":
        data = [{"name": n, "dir": d, "wlf": w, "vcd": v} for n, d, w, v in tests]
        print_json(data)
    else:
        headers = ["Test", "WLF", "VCD"]
        rows = []
        for name, _, has_wlf, has_vcd in tests:
            # Truncate long test names for readability
            display = name if len(name) <= 80 else name[:77] + "..."
            rows.append([display, "yes" if has_wlf else "no", "yes" if has_vcd else "no"])
        print_table(headers, rows)
    return 0


def cmd_list_signals(args, engine):
    signals = engine.list_signals(args.filter)
    if args.format == "json":
        data = [{"signal": s, "width": w, "type": t} for s, w, t in signals]
        print_json(data)
    else:
        headers = ["Signal", "Width", "Type"]
        rows = [[s, str(w), t] for s, w, t in signals]
        print_table(headers, rows)
    return 0


def cmd_value_at(args, engine):
    times = [parse_time(t) for t in args.time]
    results = engine.value_at(args.signal, times)
    if args.format == "json":
        data = [{"time_ps": t, "signal": s, "value_bin": v, "value_hex": format_value_hex(v)}
                for t, s, v in results]
        print_json(data)
    else:
        headers = ["Time", "Signal", "Value (bin)", "Value (hex)"]
        rows = [[format_time(t), s, v, format_value_hex(v)] for t, s, v in results]
        print_table(headers, rows)
    return 0


def cmd_transitions(args, engine):
    from_ps = parse_time(args.time_from) if args.time_from else None
    to_ps = parse_time(args.time_to) if args.time_to else None
    sig_name, results = engine.transitions(args.signal, from_ps, to_ps)
    if args.format == "json":
        data = [{"time_ps": t, "value_bin": v, "value_hex": format_value_hex(v)}
                for t, v in results]
        print_json({"signal": sig_name, "transitions": data})
    else:
        print(f"Signal: {sig_name}")
        headers = ["Time", "Value (bin)", "Value (hex)"]
        rows = [[format_time(t), v, format_value_hex(v)] for t, v in results]
        print_table(headers, rows)
    return 0


def cmd_find_edge(args, engine):
    sig_name, t, prev, curr = engine.find_edge(args.signal, args.edge, args.nth)
    if t is None:
        print(f"No {args.edge} edge #{args.nth} found for {sig_name}")
        return 1
    if args.format == "json":
        print_json({"signal": sig_name, "edge": args.edge, "nth": args.nth,
                     "time_ps": t, "value_before": prev, "value_after": curr})
    else:
        print(f"Edge #{args.nth} {args.edge} of {sig_name} at {format_time(t)}  ({prev} -> {curr})")
    return 0


def cmd_duration(args, engine):
    after_ps = parse_time(args.after) if args.after else 0
    sig_name, start, end, dur = engine.duration(args.signal, args.value, after_ps)
    if start is None:
        print(f"Signal {sig_name} never holds value {args.value} after {format_time(after_ps)}")
        return 1
    if args.format == "json":
        print_json({"signal": sig_name, "value": args.value,
                     "start_ps": start, "end_ps": end, "duration_ps": dur})
    else:
        print(f"Signal {sig_name} holds value {args.value} "
              f"from {format_time(start)} to {format_time(end)} "
              f"(duration: {format_time(dur)})")
    return 0


def cmd_compare(args, engine):
    # Parse --expect "1us=0010,5us=1000"
    pairs = []
    for item in args.expect.split(","):
        item = item.strip()
        if "=" not in item:
            raise ValueError(f"Invalid expect format '{item}'. Use 'TIME=VALUE'.")
        time_str, val = item.split("=", 1)
        pairs.append((parse_time(time_str.strip()), val.strip()))

    sig_name, results = engine.compare(args.signal, pairs)
    passed = sum(1 for *_, m in results if m)
    total = len(results)

    if args.format == "json":
        data = [{"time_ps": t, "expected": e, "actual": a, "match": m}
                for t, e, a, m in results]
        print_json({"signal": sig_name, "results": data,
                     "passed": passed, "total": total})
    else:
        print(f"Signal: {sig_name}")
        headers = ["Time", "Expected", "Actual", "Match"]
        rows = [[format_time(t), e, a, "PASS" if m else "FAIL"]
                for t, e, a, m in results]
        print_table(headers, rows)
        print(f"\nResult: {passed}/{total} passed")
    return 0 if passed == total else 1


def cmd_fsm(args, engine):
    # Parse --names "IDLE=0001,BOOT=0010,RUN=0100"
    state_names = {}
    if args.names:
        for item in args.names.split(","):
            item = item.strip()
            if "=" not in item:
                raise ValueError(f"Invalid name format '{item}'. Use 'NAME=VALUE'.")
            name, val = item.split("=", 1)
            state_names[val.strip()] = name.strip()

    sig_name, results = engine.fsm(args.signal, state_names)

    if args.format == "json":
        data = [{"time_ps": t, "value": v, "state": n, "duration_ps": d}
                for t, v, n, d in results]
        print_json({"signal": sig_name, "states": data})
    else:
        print(f"Signal: {sig_name}")
        headers = ["Time", "Value", "State", "Duration"]
        rows = [[format_time(t), v, n, format_time(d)] for t, v, n, d in results]
        print_table(headers, rows)
        print(f"\nTotal state transitions: {len(results)}")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="wavequery",
        description="Query FPGA simulation waveform data (VCD/WLF).",
    )

    # Global options
    source = parser.add_argument_group("waveform source (pick one)")
    source.add_argument("--test", metavar="PATTERN",
                        help="Test name pattern (glob-style, e.g. '*boot*fail*')")
    source.add_argument("--vcd", metavar="PATH",
                        help="Direct path to a VCD file")
    source.add_argument("--wlf", metavar="PATH",
                        help="Direct path to a WLF file (converts to VCD)")
    parser.add_argument("--vunit-out", metavar="PATH", default=None,
                        help="VUnit output directory (default: <repo>/sim/vunit_out or <repo>/vunit_out)")
    parser.add_argument("--format", choices=["table", "json"], default="table",
                        help="Output format (default: table)")

    sub = parser.add_subparsers(dest="command", required=True)

    # list-tests
    p = sub.add_parser("list-tests", help="List tests with WLF/VCD files")
    p.add_argument("--pattern", metavar="GLOB", default="*",
                   help="Filter test names (default: *)")

    # list-signals
    p = sub.add_parser("list-signals", help="List signals in a waveform")
    p.add_argument("--filter", metavar="GLOB",
                   help="Filter signal names (case-insensitive glob)")

    # value-at
    p = sub.add_parser("value-at", help="Get signal value(s) at specific time(s)")
    p.add_argument("--signal", required=True, metavar="PATTERN",
                   help="Signal name or glob pattern")
    p.add_argument("--time", required=True, nargs="+", metavar="TIME",
                   help="Time(s) to query (e.g. 500ns 1us 2.5us)")

    # transitions
    p = sub.add_parser("transitions", help="List signal transitions in a time range")
    p.add_argument("--signal", required=True, metavar="PATTERN",
                   help="Signal name or glob pattern")
    p.add_argument("--from", dest="time_from", metavar="TIME",
                   help="Start time (default: beginning)")
    p.add_argument("--to", dest="time_to", metavar="TIME",
                   help="End time (default: end of simulation)")

    # find-edge
    p = sub.add_parser("find-edge", help="Find the Nth rising/falling edge")
    p.add_argument("--signal", required=True, metavar="PATTERN",
                   help="Signal name or glob pattern")
    p.add_argument("--edge", choices=["rising", "falling", "any"], default="rising",
                   help="Edge type (default: rising)")
    p.add_argument("--nth", type=int, default=1,
                   help="Which occurrence (default: 1)")

    # duration
    p = sub.add_parser("duration", help="How long a signal holds a value")
    p.add_argument("--signal", required=True, metavar="PATTERN",
                   help="Signal name or glob pattern")
    p.add_argument("--value", required=True,
                   help="Binary value to look for (e.g. '0010')")
    p.add_argument("--after", metavar="TIME", default="0ps",
                   help="Search after this time (default: 0ps)")

    # compare
    p = sub.add_parser("compare", help="Compare expected vs actual values")
    p.add_argument("--signal", required=True, metavar="PATTERN",
                   help="Signal name or glob pattern")
    p.add_argument("--expect", required=True,
                   help="Comma-separated TIME=VALUE pairs (e.g. '1us=0010,5us=1000')")

    # fsm
    p = sub.add_parser("fsm", help="Trace state machine transitions")
    p.add_argument("--signal", required=True, metavar="PATTERN",
                   help="Signal name or glob pattern")
    p.add_argument("--names", metavar="MAP",
                   help="Comma-separated NAME=VALUE pairs (e.g. 'IDLE=00,BOOT=01,RUN=10')")

    args = parser.parse_args()

    # Determine vunit_out directory.
    # Open Logic puts it under sim/vunit_out; older / vendored projects may use <repo>/vunit_out.
    if args.vunit_out:
        vunit_out = args.vunit_out
    elif (_repo_root / "sim" / "vunit_out").exists():
        vunit_out = str(_repo_root / "sim" / "vunit_out")
    else:
        vunit_out = str(_repo_root / "vunit_out")

    converter = WlfToVcdConverter()
    finder = TestFinder(vunit_out)

    try:
        if args.command == "list-tests":
            return cmd_list_tests(args, finder)

        # All other commands need a VCD source
        vcd_path = resolve_vcd(args, converter, finder)
        engine = VcdQueryEngine(vcd_path)

        if args.command == "list-signals":
            return cmd_list_signals(args, engine)
        elif args.command == "value-at":
            return cmd_value_at(args, engine)
        elif args.command == "transitions":
            return cmd_transitions(args, engine)
        elif args.command == "find-edge":
            return cmd_find_edge(args, engine)
        elif args.command == "duration":
            return cmd_duration(args, engine)
        elif args.command == "compare":
            return cmd_compare(args, engine)
        elif args.command == "fsm":
            return cmd_fsm(args, engine)

    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
