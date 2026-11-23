# pipeline-runner

## Purpose
Describe a small data-cleaning job in a YAML file and run it with one command, repeatably. A pipeline is a list of steps applied in order to a CSV table: read it, filter rows, compute new columns, join another file, group and total, sort, trim, and write the result. Because the steps live in a file, you can review them, keep them in git and rerun them whenever the data changes, without writing code.

## Install
Needs PyYAML (JSON pipeline files work too):
```bash
pip install -r requirements.txt
```

## Usage
```bash
python pipeline_runner.py pipeline.yml [--apply]
```
```yaml
name: top orders report
steps:
  - read: orders.csv
  - filter: {column: qty, op: ">=", value: 2}
  - add_column: {name: total, expr: "qty * price"}
  - sort: {by: total, desc: true}
  - select: [order_id, product, qty, price, total]
  - limit: 5
  - write: top-orders.csv
```
Steps: `read` (path or `{file, delimiter}`), `filter` (`column`, `op`, `value`; ops `== != > >= < <= contains startswith endswith matches is_empty not_empty`), `select`, `drop`, `rename` (`{old: new}`), `sort` (`by`, `desc`), `dedupe` (columns), `limit`, `fill` (`column`, `value`), `add_column` (`name` plus `expr`, `template` such as `"{first} {last}"`, or `value`), `group` (`by`, `agg: {column: sum|mean|min|max|count}`), `join` (`file`, `on`, optional `right_on`, `how: left|inner`) and `write`. Expressions allow only numbers, column names and `+ - * / % //`. **Dry run by default:** everything runs in memory and a preview is shown; `write` only creates its file with `--apply`, and never overwrites an existing file. A failing step stops the run and names its number.

## Example
```bash
python pipeline_runner.py pipeline.yml
```
```
Pipeline: top orders report

 1. read orders.csv                                                        -> 12 row(s), 6 column(s)
 2. filter {"column": "qty", "op": ">=", "value": 2}                       -> 8 row(s), 6 column(s)
 3. add_column {"name": "total", "expr": "qty * price"}                    -> 8 row(s), 7 column(s)
 4. sort {"by": "total", "desc": true}                                     -> 8 row(s), 7 column(s)
 5. select ["order_id", "product", "qty", "price", "total"]                -> 8 row(s), 5 column(s)
 6. limit 5                                                                -> 5 row(s), 5 column(s)
 7. write top-orders.csv                                                   -> 5 row(s), 5 column(s)

Result (first 5 of 5 row(s)):
  order_id | product   | qty | price | total
  ---------+-----------+-----+-------+------
  1011     | Backpack  | 3   | 39.9  | 119.7
  1007     | Backpack  | 2   | 39.9  | 79.8
  1004     | Notebook  | 10  | 4.5   | 45
  1005     | Desk lamp | 2   | 22.0  | 44
  1006     | Pen set   | 4   | 7.25  | 29

Would write top-orders.csv (5 row(s)). Use --apply to do it.
```

## Notes
- All values are read as text; comparing and sorting treat numbers as numbers when both sides look numeric.
- Column names in expressions must not contain spaces (use a `rename` step first).
- Use `csv-differ` to compare a pipeline's output between runs and `csv-schema-validator` to check it.
