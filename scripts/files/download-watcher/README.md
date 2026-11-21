# download-watcher

## Purpose
Keep your Downloads folder tidy without thinking about it. The tool sorts the files in a folder into subfolders by type: Images, Documents, Data, Archives, Audio, Video, Installers, Code and Other. It leaves downloads that are still in progress (`.crdownload`, `.part`, `.tmp`, hidden files) and files that changed in the last few seconds alone, so it never moves a half-finished download. If a file with the same name is already in the destination, the new one gets `(1)`, `(2)`... so nothing is overwritten.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python download_watcher.py [FOLDER] [--watch] [--interval 10] [--seconds N] [--settle 5] [--apply]
```
`FOLDER` defaults to your `Downloads` folder. **Dry run by default:** it lists where each file would go. With `--apply` the files are moved. One pass is made unless you add `--watch`, which keeps sorting new arrivals every `--interval` seconds until you press Ctrl-C (or `--seconds` runs out). Existing subfolders are never touched.

## Example
```bash
python download_watcher.py downloads/ --settle 0
```
```
{{OUTPUT}}
```

## Notes
- Moves stay inside the same folder, so they are quick and keep the files' dates.
- Because moving is easy to reverse by hand, the tool doesn't keep an undo log; review the dry run first.
- The categories are listed in the script (`CATEGORIES`) if you want to add your own file types.
- Use `folder-watcher` to run your own command on new files instead.
