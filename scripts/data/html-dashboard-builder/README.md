# html-dashboard-builder

## Purpose
Turn a small JSON file into a single, self-contained HTML dashboard: metric cards with up/down
changes, line and bar charts (inline SVG) and tables. No JavaScript, no internet needed, and it
follows the reader's light or dark mode.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python html_dashboard_builder.py data.json --output dashboard.html
python html_dashboard_builder.py data.json > dashboard.html
```

The JSON can contain any of:
```
{"title": "...", "subtitle": "...",
 "metrics": [{"label": "Revenue", "value": 48210, "unit": "$", "change": 3.1,
              "lower_is_better": false}],
 "charts":  [{"title": "Signups", "type": "line" or "bar", "labels": [...], "values": [...]}],
 "tables":  [{"title": "Top pages", "columns": [...], "rows": [[...], ...]}]}
```
`change` is a percentage. Set `lower_is_better` for things like churn or open bugs, so a drop is
shown in green. `--output` refuses to overwrite a file unless you add `--force`.

## Example
`dashboard-data.json --output dashboard.html`

```
Wrote dashboard.html (5,959 bytes). It needs no internet connection.
```

## Notes
- All text from the JSON is HTML-escaped.
- Charts have tooltips and text labels for screen readers; tables use real header cells.
- Chart values should be numbers; the y axis starts at zero.
