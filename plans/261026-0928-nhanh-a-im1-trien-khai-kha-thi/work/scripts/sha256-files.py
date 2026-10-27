"""Print the sha256 of each file argument (one line per file)."""
import hashlib
import sys

for path in sys.argv[1:]:
    with open(path, "rb") as f:
        print(hashlib.sha256(f.read()).hexdigest(), path)
