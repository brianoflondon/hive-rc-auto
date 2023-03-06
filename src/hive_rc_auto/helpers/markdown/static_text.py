from glob import glob
from os.path import dirname, exists
from pathlib import Path

ALL_MARKDOWN = {}


def import_text():
    files = glob(f"{dirname(__file__)}/*.md")
    for filepath in files:
        if exists(filepath):
            with open(filepath, "r") as f:
                file = Path(filepath).stem
                ALL_MARKDOWN[file] = f.read()
    return ALL_MARKDOWN
