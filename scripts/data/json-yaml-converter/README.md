# json-yaml-converter

## Purpose
Convert configuration and data files between JSON and YAML, keeping key order and non-ASCII text intact.

## Install
Needs PyYAML:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python json_yaml_converter.py FILE [--to json|yaml] [-o OUTPUT --apply]
```
The input format comes from the file extension (`.yaml` / `.yml` or anything else as JSON), and the target defaults to the opposite one. The result is printed unless you pass `-o` together with `--apply`.

## Example
```bash
python json_yaml_converter.py config.json
```
```
name: demo
ports:
- 80
- 443
debug: false
```

## Notes
- Uses `yaml.safe_load`, so YAML files cannot run code.
- YAML features with no JSON equivalent (anchors, comments) are resolved or dropped in the conversion.
- Invalid input exits with 1 and an error message.
