"""Convert CSV to Parquet and back, with a size and schema report."""
import argparse
import contextlib
import sys
from pathlib import Path

import pandas as pd

with contextlib.suppress(ImportError):  # lets the browser demo load a Parquet engine
    import fastparquet  # noqa: F401

COMPRESSION = {"snappy": "snappy", "gzip": "gzip", "zstd": "zstd", "none": None}


def human(size):
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def direction(source):
    suffix = source.suffix.lower()
    if suffix in (".csv", ".tsv", ".txt"):
        return "to_parquet"
    if suffix in (".parquet", ".pq"):
        return "to_csv"
    raise ValueError(f"don't know how to convert '{source.suffix}' files (use .csv or .parquet)")


def describe(frame):
    return [(str(name), str(dtype), int(frame[name].isna().sum()))
            for name, dtype in frame.dtypes.items()]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert between CSV and Parquet.")
    parser.add_argument("source", type=Path, help="a .csv or a .parquet file")
    parser.add_argument("-o", "--output", type=Path,
                        help="file to create (default: same name with the other extension)")
    parser.add_argument("--compression", choices=list(COMPRESSION), default="snappy",
                        help="Parquet compression (snappy)")
    parser.add_argument("--delimiter", default=",", help="field separator for CSV input (,)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the file (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.source.is_file():
        parser.error(f"not a file: {args.source}")
    try:
        mode = direction(args.source)
    except ValueError as err:
        parser.error(str(err))
    default_suffix = ".parquet" if mode == "to_parquet" else ".csv"
    output = args.output or args.source.with_suffix(default_suffix)

    try:
        frame = (pd.read_csv(args.source, sep="\t" if args.source.suffix == ".tsv"
                             else args.delimiter) if mode == "to_parquet"
                 else pd.read_parquet(args.source))
    except ImportError:
        print("Reading or writing Parquet needs pyarrow or fastparquet: pip install pyarrow",
              file=sys.stderr)
        return 1
    except (ValueError, OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as err:
        print(f"Can't read {args.source.name}: {err}", file=sys.stderr)
        return 1

    print(f"{args.source.name}: {len(frame)} row(s) x {len(frame.columns)} column(s), "
          f"{human(args.source.stat().st_size)}")
    for name, dtype, missing in describe(frame):
        print(f"  {name:<20} {dtype:<16}" + (f" {missing} missing" if missing else ""))
    if not args.apply:
        kind = f"Parquet, {args.compression}" if mode == "to_parquet" else "CSV"
        print(f"\nWould create {output.name} ({kind}). Use --apply to do it.")
        return 0
    if output.exists():
        print(f"{output} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    try:
        if mode == "to_parquet":
            frame.to_parquet(output, index=False, compression=COMPRESSION[args.compression])
        else:
            frame.to_csv(output, index=False)
    except ImportError:
        print("Writing Parquet needs pyarrow or fastparquet: pip install pyarrow", file=sys.stderr)
        return 1
    except (ValueError, OSError) as err:
        print(f"Can't write {output.name}: {err}", file=sys.stderr)
        output.unlink(missing_ok=True)
        return 1
    before, after = args.source.stat().st_size, output.stat().st_size
    change = f"{100 * (before - after) // before}% smaller" if after < before else (
        f"{100 * (after - before) // max(before, 1)}% larger")
    print(f"\nSaved {output.name}: {human(after)} ({change} than the original).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
