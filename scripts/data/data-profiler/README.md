# data-profiler

## Purpose
Get to know a dataset in seconds. For every column of a CSV file the profiler shows the detected type (integer, decimal, date, true/false or text), how many values are present and missing, how many are unique, and a summary suited to the type: minimum, quartiles, median, mean, standard deviation and a text histogram for numbers; length and the most common values for text. It also warns about things worth a look: mostly-empty columns, constant columns, identifier-like columns, and numeric columns polluted with stray text.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python data_profiler.py data.csv [--columns age,status] [--top 5] [--bins 6] [--delimiter ";"]
```
Missing values are empty cells and the markers `NA`, `N/A`, `null`, `none`, `nan`, `-` and `?`. `--top` sets how many common values are listed and `--bins` how many histogram bars numbers get. A summary line gives the number of rows and duplicate rows.

## Example
```bash
python data_profiler.py customers.csv --columns age,status,score
```
```
{{OUTPUT}}
```

## Notes
- Types are guessed from the values, so one stray text value turns a number column into text (and the profiler warns you about it).
- For files with millions of rows use a tool built for scale; this one reads the file into memory.
- Use `csv-schema-validator` to turn what you learn into enforceable rules.
