# docker-image-reporter

## Purpose
Find out what is eating your disk space. The tool lists your local Docker images from the biggest to the smallest with their age, flags the large ones (over 500 MB), counts the "dangling" images (untagged leftovers from rebuilds that `docker image prune` can remove) and points out repositories that keep several big old tags.

## Install
Needs Docker installed and running (for live use). No Python packages are required.

## Usage
```bash
python docker_image_reporter.py [--top 10]
python docker_image_reporter.py --from-file images.jsonl
```
Without options it runs `docker images --format "{{json .}}"` for you. `--from-file` reads output you saved earlier, for example on another machine: `docker images --format "{{json .}}" > images.jsonl`. `--top` limits how many images are listed. The tool only reads; it never removes anything.

## Example
```bash
python docker_image_reporter.py --from-file docker-images.jsonl --top 6
```
```
{{OUTPUT}}
```

## Notes
- Docker reports sizes in decimal units (1 GB = 1000 MB), and the tool does too.
- Images share layers, so the total is the sum of the listed sizes and the real disk use is usually lower. `docker system df` shows the true figure.
- If Docker isn't installed the tool says so instead of crashing.
- The website demo reads a saved list; your real images are reported on your own computer.
