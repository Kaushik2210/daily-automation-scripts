# repo-readme-generator

## Purpose
Get a README draft instead of a blank page. It looks at the project folder and writes a starting point with the project name and description, the main languages, install and run commands, a short folder tree and the license.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python repo_readme_generator.py [FOLDER] [-o README.md --apply]
```
The draft is printed. To save it pass `-o` with `--apply`; an existing file is never overwritten.

## Example
```bash
python repo_readme_generator.py demo-project
```
````
# shop-demo

A tiny demo storefront

Built with JavaScript.

## Getting started

```bash
npm install
npm start
npm run test
npm run build
```

## Project structure

```
src/
  app.js
  utils.js
tests/
  app.test.js
LICENSE
package.json
```

## License

MIT.
````

## Notes
- It understands `package.json` (name, description, scripts, license), `requirements.txt` and `pyproject.toml`.
- It is a draft: fill in the description, usage examples and screenshots yourself.
- `.git`, `node_modules`, virtual environments and build folders are left out of the tree.
