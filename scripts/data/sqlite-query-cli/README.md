# sqlite-query-cli

## Purpose
Ask questions of a SQLite database from the terminal, without installing a database tool. Run any SQL query and get a neat aligned table (or CSV, JSON or markdown for other programs), list the tables with their row counts, or print their `CREATE` statements. The database is opened **read-only** by default, so a mistyped `DELETE` can't hurt anything.

## Install
Standard library only, Python 3.11+. Nothing to install (SQLite is built into Python).

## Usage
```bash
python sqlite_query_cli.py shop.db "SELECT * FROM customers LIMIT 5" [--format table|csv|json|markdown] [--limit 50]
python sqlite_query_cli.py shop.db --tables
python sqlite_query_cli.py shop.db --schema
python sqlite_query_cli.py shop.db "UPDATE customers SET country = 'IN' WHERE id = 1" --write [--apply]
```
One statement per call. Table output right-aligns numbers, shows missing values as `NULL`, shortens very long text and prints the first `--limit` rows (0 for all). Statements that change data need `--write`, and even then they are a **dry run** that reports how many rows would change; add `--apply` to keep the changes. The exit code is 1 when the SQL fails.

## Example
```bash
python sqlite_query_cli.py shop.db "SELECT c.name, COUNT(o.order_id) AS orders, ROUND(SUM(o.qty * o.price), 2) AS spent FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id ORDER BY spent DESC"
```
```
name          | orders | spent
--------------+--------+------
Ben Carter    |      2 | 87.05
Asha Rao      |      3 |  80.4
Diego Alvarez |      2 |  67.0
Emma Wilson   |      2 |  48.0
Chloe Martin  |      1 |  44.0
Farid Khan    |      1 |   9.5

6 row(s)
```

## Notes
- Create a database from CSV files with `sqlite-csv-importer`, or from logs with `log-to-sqlite`.
- Quote the whole query so your shell doesn't treat `*` or `;` specially.
- Only SQLite files are supported (not MySQL or PostgreSQL).
