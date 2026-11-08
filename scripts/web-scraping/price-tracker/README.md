# price-tracker

## Purpose
Know when something gets cheaper. It reads the price of a product page, compares it with the readings you saved before, and tells you whether it dropped, rose or stayed the same, and whether it's the lowest price yet. Every run can add a row to a CSV, so a daily schedule builds a price history you can chart.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python price_tracker.py SOURCE [--history prices.csv] [--no-record] [--target 50] [--regex PATTERN]
```
`SOURCE` is a product URL or a saved `.html` file. The price is looked up in the page's structured data first, then meta tags and `itemprop="price"`, then your `--regex` (one capture group), and finally the first price with a currency symbol. Without `--history` it just prints the price.

## Example
```bash
python price_tracker.py product.html --history prices.csv --no-record --target 80
```
```
Price now: 79.99 USD
PRICE DROP: 10.00 less than 89.99 on 2026-10-15 (11.1%)
Lowest price seen so far!
At or below your target of 80.00.
(read from structured data)
```

## Notes
- The history CSV has the columns `timestamp, url, price, currency`; each page is tracked by the exact source you gave.
- `--no-record` compares without adding a row, handy for trying a new page.
- Run it from cron or Task Scheduler for a real tracker. Pick a sensible interval, such as once a day.
- Shops that load prices with JavaScript may not show one in the raw HTML; use `--regex` or a saved copy of the rendered page.
- On the website demo only saved files can be read; fetching a URL works on your own computer.
