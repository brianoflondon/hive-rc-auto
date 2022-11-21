from os.path import dirname, join, exists, split
from pathlib import Path
from glob import glob

# files = ['rc_overview.md', 'podping_health.md', 'pings']

ALL_MARKDOWN= {}

files = glob(f"{dirname(__file__)}/*.md")

for filepath in files:
    if exists(filepath):
        with open(filepath, 'r') as f:
            file = Path(filepath).stem
            ALL_MARKDOWN[file] = f.read()
