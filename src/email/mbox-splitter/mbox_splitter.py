"""Split an mbox mail export into one file per month. Dry run by default."""
import argparse
import mailbox
import sys
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path


def month_of(msg):
    """YYYY-MM for a message, from its Date header or else the mbox 'From ' line."""
    try:
        return parsedate_to_datetime(str(msg["Date"])).strftime("%Y-%m")
    except (TypeError, ValueError):
        pass
    parts = (msg.get_from() or "").split(None, 1)
    if len(parts) == 2:
        try:
            return datetime.strptime(parts[1].strip(), "%a %b %d %H:%M:%S %Y").strftime("%Y-%m")
        except ValueError:
            pass
    return "unknown-date"


def group_by_month(box):
    groups = defaultdict(list)
    for key, msg in box.items():
        groups[month_of(msg)].append(key)
    return dict(sorted(groups.items()))


def human_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def main(argv=None):
    parser = argparse.ArgumentParser(description="Split an mbox file by month.")
    parser.add_argument("source", type=Path, help="the mbox file to split")
    parser.add_argument("--out-dir", type=Path,
                        help="where to write the pieces (default: next to the source)")
    parser.add_argument("--prefix", default="", help="text to put before each file name")
    parser.add_argument("--apply", action="store_true", help="actually write the files")
    args = parser.parse_args(argv)
    if not args.source.is_file():
        parser.error(f"not a file: {args.source}")

    try:
        box = mailbox.mbox(str(args.source))
        groups = group_by_month(box)
    except (OSError, mailbox.Error) as err:
        print(f"Couldn't read {args.source}: {err}", file=sys.stderr)
        return 1
    if not groups:
        print("The mbox file is empty.")
        return 1

    out_dir = args.out_dir or args.source.parent
    written = skipped = 0
    for month, keys in groups.items():
        target = out_dir / f"{args.prefix}{month}.mbox"
        size = sum(len(box[k].as_bytes()) for k in keys)
        line = f"{target.name}: {len(keys)} message(s), {human_size(size)}"
        if target.exists():
            print(f"{line} - skipped, {target} already exists")
            skipped += 1
        elif not args.apply:
            print(f"{line} - would write")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            piece = mailbox.mbox(str(target))
            try:
                for key in keys:
                    piece.add(box[key])
                piece.flush()
            finally:
                piece.close()
            print(f"{line} - written")
            written += 1
    box.close()
    total = sum(len(keys) for keys in groups.values())
    if args.apply:
        print(f"Split {total} message(s) into {written} new file(s); "
              f"{args.source.name} was left as it was.")
    else:
        print(f"{total} message(s) would go into {len(groups) - skipped} file(s). "
              "Dry run - add --apply to write them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
