from os.path import dirname, join

files = ['rc_overview.md', 'podping_health.md']

ALL_MARKDOWN= {}
for file in files:
    filename = join(dirname(__file__), file)
    with open(filename, 'r') as f:
        ALL_MARKDOWN[file] = f.read()
