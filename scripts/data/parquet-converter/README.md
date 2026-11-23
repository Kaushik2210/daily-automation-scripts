# parquet-converter

## Purpose
Convert between CSV and Parquet, the compact column-oriented format used by data tools like pandas, Spark and DuckDB. Parquet files are typically several times smaller than the CSV they came from, remember column types (numbers stay numbers, dates stay dates) and load much faster. The tool detects the direction from the file extension, shows the columns, their types and missing-value counts, and reports the size change after converting.

## Install
Needs pandas and a Parquet engine:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python parquet_converter.py data.csv [-o data.parquet] [--compression snappy|gzip|zstd|none] [--apply]
python parquet_converter.py data.parquet -o data.csv --apply
```
**Dry run by default:** it reads the file, prints the schema and says what it would create. With `--apply` it writes the converted file next to the source (or at `-o`) and never overwrites an existing file. `--delimiter` sets the separator for CSV input (use `.tsv` files for tabs). The exit code is 1 when a file can't be read or written.

## Example
```bash
python parquet_converter.py orders.csv --apply
```
```
orders.csv: 12 row(s) x 6 column(s), 452 B
  order_id             int64           
  customer_id          int64           
  product              str             
  qty                  int64           
  price                float64         
  ordered_at           str             

Saved orders.parquet: 4.1 KB (832% larger than the original).
```

## Notes
- Parquet pays off with more data: tiny files like the demo can even grow because of the format's fixed overhead.
- Column types come from pandas' guess; empty cells in a whole-number column make it decimal (`float64`).
- Use `csv-to-json` or `json-to-csv` for text formats, and `sqlite-csv-importer` for a database.
- The website demo uses the `fastparquet` engine; on your computer `pyarrow` is used.
