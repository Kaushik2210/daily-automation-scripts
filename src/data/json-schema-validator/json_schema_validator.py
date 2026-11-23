"""Validate JSON files against a JSON Schema (a practical subset of drafts 6 and 7)."""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TYPES = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list,
         "object": dict, "null": type(None)}
FORMATS = {
    "email": r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$",
    "uri": r"^[A-Za-z][A-Za-z0-9+.-]*://\S+$",
    "ipv4": r"^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$",
    "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
}


def is_type(value, name):
    """JSON Schema types: True is not a number, and 3.0 counts as an integer."""
    if name == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPES[name])


def resolve(ref, root):
    if ref == "#":
        return root
    if not ref.startswith("#/"):
        raise ValueError(f"only local references are supported, not '{ref}'")
    node = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise ValueError(f"can't resolve the reference '{ref}'")
        node = node[part]
    return node


def valid_format(value, name):
    if name == "date":
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return False
        return True
    if name == "date-time":
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?"
                             r"([Zz]|[+-]\d{2}:\d{2})?$", value))
    return name not in FORMATS or bool(re.match(FORMATS[name], value))


def validate(value, schema, root=None, path="$"):
    """Return a list of (path, message) for everything that breaks the schema."""
    root = root if root is not None else schema
    if schema is True or schema is None:
        return []
    if schema is False:
        return [(path, "no value is allowed here")]
    errors = []
    if "$ref" in schema:
        return validate(value, resolve(schema["$ref"], root), root, path)
    kinds = schema.get("type")
    if kinds is not None:
        names = [kinds] if isinstance(kinds, str) else kinds
        if not any(is_type(value, n) for n in names):
            return [(path, f"is {type_name(value)}, expected {' or '.join(names)}")]
    if "enum" in schema and value not in schema["enum"]:
        errors.append((path, f"must be one of {', '.join(json.dumps(v) for v in schema['enum'])}"))
    if "const" in schema and value != schema["const"]:
        errors.append((path, f"must equal {json.dumps(schema['const'])}"))
    if isinstance(value, str):
        errors += check_string(value, schema, path)
    if is_type(value, "number"):
        errors += check_number(value, schema, path)
    if isinstance(value, list):
        errors += check_array(value, schema, root, path)
    if isinstance(value, dict):
        errors += check_object(value, schema, root, path)
    errors += check_combinators(value, schema, root, path)
    return errors


def type_name(value):
    if value is None:
        return "null"
    for name in ("boolean", "integer", "number", "string", "array", "object"):
        if is_type(value, name):
            return name
    return type(value).__name__


def check_string(value, schema, path):
    errors = []
    if "minLength" in schema and len(value) < schema["minLength"]:
        errors.append((path, f"is shorter than {schema['minLength']} character(s)"))
    if "maxLength" in schema and len(value) > schema["maxLength"]:
        errors.append((path, f"is longer than {schema['maxLength']} character(s)"))
    if "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append((path, f"does not match the pattern {schema['pattern']}"))
    if "format" in schema and not valid_format(value, schema["format"]):
        errors.append((path, f"is not a valid {schema['format']}"))
    return errors


def check_number(value, schema, path):
    errors = []
    if "minimum" in schema and value < schema["minimum"]:
        errors.append((path, f"is below the minimum of {schema['minimum']}"))
    if "maximum" in schema and value > schema["maximum"]:
        errors.append((path, f"is above the maximum of {schema['maximum']}"))
    if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
        errors.append((path, f"must be greater than {schema['exclusiveMinimum']}"))
    if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
        errors.append((path, f"must be less than {schema['exclusiveMaximum']}"))
    if "multipleOf" in schema and schema["multipleOf"] and abs(
            value / schema["multipleOf"] - round(value / schema["multipleOf"])) > 1e-9:
        errors.append((path, f"is not a multiple of {schema['multipleOf']}"))
    return errors


def check_array(value, schema, root, path):
    errors = []
    if "minItems" in schema and len(value) < schema["minItems"]:
        errors.append((path, f"has fewer than {schema['minItems']} item(s)"))
    if "maxItems" in schema and len(value) > schema["maxItems"]:
        errors.append((path, f"has more than {schema['maxItems']} item(s)"))
    if schema.get("uniqueItems"):
        seen = []
        for index, item in enumerate(value):
            if item in seen:
                errors.append((f"{path}[{index}]", "is a duplicate of an earlier item"))
            seen.append(item)
    items = schema.get("items")
    if isinstance(items, list):
        for index, (item, sub) in enumerate(zip(value, items, strict=False)):
            errors += validate(item, sub, root, f"{path}[{index}]")
    elif items is not None:
        for index, item in enumerate(value):
            errors += validate(item, items, root, f"{path}[{index}]")
    return errors


def check_object(value, schema, root, path):
    errors = []
    for name in schema.get("required", []):
        if name not in value:
            errors.append((path, f"is missing the required property '{name}'"))
    properties = schema.get("properties", {})
    patterns = schema.get("patternProperties", {})
    for name, item in value.items():
        where = f"{path}.{name}"
        matched = False
        if name in properties:
            errors += validate(item, properties[name], root, where)
            matched = True
        for pattern, sub in patterns.items():
            if re.search(pattern, name):
                errors += validate(item, sub, root, where)
                matched = True
        if not matched and "additionalProperties" in schema:
            extra = schema["additionalProperties"]
            if extra is False:
                errors.append((where, "is not an allowed property"))
            elif extra is not True:
                errors += validate(item, extra, root, where)
    if "minProperties" in schema and len(value) < schema["minProperties"]:
        errors.append((path, f"has fewer than {schema['minProperties']} propert(ies)"))
    if "maxProperties" in schema and len(value) > schema["maxProperties"]:
        errors.append((path, f"has more than {schema['maxProperties']} propert(ies)"))
    return errors


def check_combinators(value, schema, root, path):
    errors = []
    for sub in schema.get("allOf", []):
        errors += validate(value, sub, root, path)
    if "anyOf" in schema and not any(not validate(value, s, root, path) for s in schema["anyOf"]):
        errors.append((path, "does not match any of the allowed shapes (anyOf)"))
    if "oneOf" in schema:
        matches = sum(not validate(value, s, root, path) for s in schema["oneOf"])
        if matches != 1:
            errors.append((path, f"matches {matches} of the oneOf shapes, exactly 1 is required"))
    if "not" in schema and not validate(value, schema["not"], root, path):
        errors.append((path, "matches a shape that is not allowed"))
    if "if" in schema:
        branch = "then" if not validate(value, schema["if"], root, path) else "else"
        if branch in schema:
            errors += validate(value, schema[branch], root, path)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate JSON files against a JSON Schema.")
    parser.add_argument("schema", type=Path)
    parser.add_argument("files", nargs="+", type=Path, help="JSON files or folders")
    parser.add_argument("--max-errors", type=int, default=10, help="problems per file (10)")
    args = parser.parse_args(argv)
    try:
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print(f"Can't read the schema: {err}", file=sys.stderr)
        return 1

    files = []
    for path in args.files:
        files += sorted(path.rglob("*.json")) if path.is_dir() else [path]
    if not files:
        print("No JSON files found.", file=sys.stderr)
        return 1
    invalid = 0
    for path in files:
        try:
            errors = validate(json.loads(path.read_text(encoding="utf-8-sig")), schema)
        except (OSError, ValueError) as err:
            print(f"{path.name}: can't be read ({err})")
            invalid += 1
            continue
        if not errors:
            print(f"{path.name}: valid")
            continue
        invalid += 1
        print(f"{path.name}: {len(errors)} problem(s)")
        for where, message in errors[:args.max_errors]:
            print(f"  {where} {message}")
        if len(errors) > args.max_errors:
            print(f"  ... and {len(errors) - args.max_errors} more")
    print(f"\n{len(files) - invalid} of {len(files)} file(s) valid.")
    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())
