# json-schema-validator

## Purpose
Check that JSON files have the shape you expect: the right fields, types and values. Write the rules once in a JSON Schema and the tool validates one file or a whole folder, listing every problem with its exact location (`$.address.zip`, `$.tags[1]`) in plain words. It implements the commonly used parts of JSON Schema (drafts 6 and 7) itself, so there is nothing to install.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python json_schema_validator.py schema.json FILE_OR_FOLDER [...] [--max-errors 10]
```
Folders are searched recursively for `.json` files. Supported keywords: `type` (including lists of types), `enum`, `const`, `required`, `properties`, `patternProperties`, `additionalProperties`, `items` (one schema or a list), `minItems`, `maxItems`, `uniqueItems`, `minLength`, `maxLength`, `pattern`, `format` (email, uri, date, date-time, ipv4, uuid), `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`, `minProperties`, `maxProperties`, `allOf`, `anyOf`, `oneOf`, `not`, `if`/`then`/`else` and local `$ref` references (`#/definitions/...` or `#/$defs/...`). Unknown keywords are ignored. The exit code is 1 if any file is invalid or unreadable.

## Example
```bash
python json_schema_validator.py person.schema.json people/
```
```
{{OUTPUT}}
```

## Notes
- Remote `$ref` addresses (http://...) are not fetched and give an error.
- Booleans are not numbers, and `3.0` counts as an integer, as the standard says.
- Use `csv-schema-validator` for CSV files.
