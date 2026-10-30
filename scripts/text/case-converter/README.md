# case-converter

## Purpose
Convert identifiers and phrases between naming styles: snake, kebab, camel, Pascal, Title, CONSTANT, sentence, lower and upper case. It understands camelCase, snake_case, kebab-case and plain spaced text as input.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python case_converter.py --to STYLE [TEXT ...]
```
Styles: `snake`, `kebab`, `camel`, `pascal`, `title`, `constant`, `sentence`, `lower`, `upper`. With no text it reads lines from standard input.

## Example
```bash
python case_converter.py --to snake "FirstName" "shippingAddressLine2"
```
```
first_name
shipping_address_line_2
```

## Notes
- Acronyms stay together: `HTTPServerError` becomes `http_server_error`.
- Each argument (or input line) is converted on its own line.
- Read-only.
