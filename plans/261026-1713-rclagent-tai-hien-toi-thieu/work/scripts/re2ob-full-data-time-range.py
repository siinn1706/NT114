"""Full preprocessed RE2-OB metric/log timestamp range, to know what the author's tools return far outside it.

usage: python -I -X utf8 re2ob-full-data-time-range.py DATA
"""
import json
import sys
from pathlib import Path

import pandas as pd

data = Path(sys.argv[1])
result = {}
for name, path in (('metric', 'metric/all/metrics.csv'), ('log', 'log/all/logs.csv')):
    low = high = None
    for chunk in pd.read_csv(data / path, usecols=['timestamp'], chunksize=2_000_000):
        low = chunk.timestamp.min() if low is None else min(low, chunk.timestamp.min())
        high = chunk.timestamp.max() if high is None else max(high, chunk.timestamp.max())
    result[name] = {'min_second': int(low), 'max_second': int(high)}
print(json.dumps(result, indent=2))
