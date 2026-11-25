# license-header-adder

## Purpose
Put a short license notice at the top of every source file, the way many open-source projects and the REUSE standard ask for: a copyright line, one sentence naming the license, and an `SPDX-License-Identifier` tag that tools can read. The tool knows the comment style of each language (`#`, `//`, `--`, `/* */`, `<!-- -->`), keeps shebang lines, Python encoding lines and XML declarations at the top, leaves files that already have a header alone, and preserves each file's line endings.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python license_header_adder.py PATH [PATH ...] [--license mit|apache-2.0|gpl-3.0|bsd-3-clause|isc|unlicense]
                               [--holder "Your Name"] [--year 2026] [--text-file header.txt]
                               [--ext py,js] [--apply]
```
**Dry run by default:** it lists the files that would get a header and the ones that already have one (it looks for `SPDX-License-Identifier`, "copyright" or "licensed under" in the first lines). Add `--apply` to write the changes. `--text-file` uses your own header text instead (it is wrapped in the right comment style for each file). Folders like `.git`, `node_modules`, `.venv`, `build` and `dist` are skipped, and files that can't be read as UTF-8 text are reported, not touched. Commit or back up first; the tool adds a header but cannot automatically remove it.

## Example
```bash
python license_header_adder.py pyproj/ --holder "Demo Author" --year 2026
```
```
would add  pyproj\.github\workflows\ci.yml
would add  pyproj\app\__init__.py
would add  pyproj\app\core.py
would add  pyproj\app\legacy.py
would add  pyproj\app\main.py
has header   pyproj\app\models.py
would add  pyproj\app\utils.py
would add  pyproj\tests\test_core.py

Would add headers to 7 file(s); 1 already had one or were skipped. Use --apply to do it.
```

## Notes
- This adds a short notice, not the full license text; keep the full text in a `LICENSE` file at the project root.
- Check that the license you choose is compatible with the project's dependencies and your employer's rules.
- Use `repo-health-scorer` to see whether the project has a LICENSE at all.
