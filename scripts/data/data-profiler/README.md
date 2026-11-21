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
customers.csv: 16 rows x 9 columns, 0 duplicate row(s)

age  [int]  16 values, 0 missing, 15 unique
    min 27  p25 29.25  median 35  p75 44  max 150  mean 42.94  std 29.52
           27 - 47.50     #################### 14
        47.50 - 68        #                    1
           68 - 88.50                          0
        88.50 - 109                            0
          109 - 129.50                         0
       129.50 - 150       #                    1

status  [text]  16 values, 0 missing, 3 unique
    length 6-8 (average 6.4)
    common: active (12), inactive (3), pending (1)

score  [float]  14 values, 2 missing, 14 unique
    min 58  p25 71.25  median 80.25  p75 86.62  max 91  mean 78.54  std 9.82
           58 - 63.50     #####                1
        63.50 - 69        #####                1
           69 - 74.50     ##########           2
        74.50 - 80        ###############      3
           80 - 85.50     ###############      3
        85.50 - 91        #################### 4

0 of 3 column(s) have something worth a look.
```

## Notes
- Types are guessed from the values, so one stray text value turns a number column into text (and the profiler warns you about it).
- For files with millions of rows use a tool built for scale; this one reads the file into memory.
- Use `csv-schema-validator` to turn what you learn into enforceable rules.
