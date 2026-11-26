# invoice-generator

## Purpose
Turn a small JSON file into a clean, print-ready HTML invoice with exact totals, tax and
discount. Open it in a browser and use "Print to PDF" to get a PDF.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python invoice_generator.py invoice.json --output invoice-2026-014.html
python invoice_generator.py invoice.json --format text
```

The JSON looks like this:
```
{"number": "2026-014", "date": "2026-11-20", "due_date": "2026-12-20", "currency": "USD",
 "from": {"name": "Ada Studio", "address": ["12 Analytical Way"], "email": "billing@example.com"},
 "to": {"name": "Northwind", "address": ["500 Harbour Road"]},
 "items": [{"description": "Website redesign", "quantity": 1, "unit_price": 2400}],
 "tax_rate": 8.5, "discount": 100, "notes": "Payment within 30 days."}
```
`number`, `from`, `to` and at least one item are required. `tax_rate` is a percentage and
`discount` is an amount taken off before tax. `--output` refuses to overwrite a file unless you add
`--force`.

## Example
`invoice.json --format text`

```
Invoice 2026-014 for Northwind Traders
  Website redesign                      1 x  $2,400.00 =   $2,400.00
  Extra revision rounds                 3 x    $150.00 =     $450.00
  Hosting setup (hours)               4.5 x     $80.00 =     $360.00
  Subtotal                                                $3,210.00
  Discount                                                 -$100.00
  Tax 8.5%                                                  $264.35
  TOTAL DUE                                               $3,374.35
```

## Notes
- Money uses exact decimal arithmetic, rounded half-up to cents per line and for the tax.
- Known currencies get a symbol (USD, EUR, GBP, INR, JPY); others show the code after the amount.
- All text is HTML-escaped. The page follows light/dark mode on screen and prints black on white.
