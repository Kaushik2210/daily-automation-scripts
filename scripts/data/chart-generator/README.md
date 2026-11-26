# chart-generator

## Purpose
Plot one or more numeric CSV columns as a line or bar chart. It writes a clean SVG (colour-blind
safe palette, tooltips, a title and a legend) or prints a quick bar chart in the terminal.

## Install
No dependencies beyond Python 3.11+. The SVG is built by hand, so there is no plotting library.

## Usage
```
python chart_generator.py sales.csv --x month --y revenue --output revenue.svg
python chart_generator.py sales.csv --x month --y revenue --y costs --type bar --title "2026"
python chart_generator.py sales.csv --x month --y revenue --format text
```

- `--y` can be repeated to plot several columns together.
- `--x` names the label column; without it the rows are numbered.
- Rows where a plotted column isn't a number are skipped and counted. Thousands separators
  such as `1,200` are understood.
- `--output` refuses to overwrite a file unless you add `--force`.

## Example
`sales-monthly.csv --x month --y revenue --format text`

```
revenue
  Jan | ######################### 8,928
  Feb | ########################## 9,383
  Mar | ############################# 10,444
  Apr | ################################ 11,456
  May | ################################## 11,919
  Jun | #################################### 12,779
  Jul | #################################### 12,733
  Aug | ################################### 12,489
  Sep | ################################## 12,049
  Oct | #################################### 12,823
  Nov | ####################################### 13,658
  Dec | ######################################## 14,171
```

## Notes
- The y axis always includes zero and uses round tick values.
- With many points only about a dozen x labels are drawn, so they stay readable.
