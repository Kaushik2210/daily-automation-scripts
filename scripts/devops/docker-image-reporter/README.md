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
IMAGE                           SIZE  CREATED        ID
node:20                       1.1 GB  2 months ago   c3d4e5f6a1b2  <- large
python:3.12                   1.0 GB  3 weeks ago    a1b2c3d4e5f6  <- large
myapp:latest                845.0 MB  2 days ago     f6a1b2c3d4e5  <- large
<none>                      845.0 MB  3 days ago     1b2c3d4e5f6a
myapp:1.4.0                 843.0 MB  2 weeks ago    0a1b2c3d4e5f  <- large
postgres:16                 432.0 MB  5 weeks ago    d4e5f6a1b2c3
... and 5 more

11 image(s), 5.6 GB in total (shared layers are counted once per image, so the real disk use is lower).
2 dangling image(s) using 1.1 GB: remove them with 'docker image prune'.
myapp has 2 tags (latest, 1.4.0) totalling 1.7 GB: old tags may be removable.
python has 2 tags (3.12, 3.12-slim) totalling 1.2 GB: old tags may be removable.
```

## Notes
- Docker reports sizes in decimal units (1 GB = 1000 MB), and the tool does too.
- Images share layers, so the total is the sum of the listed sizes and the real disk use is usually lower. `docker system df` shows the true figure.
- If Docker isn't installed the tool says so instead of crashing.
- The website demo reads a saved list; your real images are reported on your own computer.
