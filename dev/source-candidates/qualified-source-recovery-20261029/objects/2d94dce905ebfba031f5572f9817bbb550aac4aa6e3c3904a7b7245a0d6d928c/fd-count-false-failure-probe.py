"""Authored unrelated descriptor collection during the existing reader test."""
import gc, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from test_portfolio_bm_lc_sc import PortfolioBindingTests
from offmenu import portfolio_bm_lc_sc as portfolio

class Cycle:
    def __init__(self):
        self.stream = tempfile.TemporaryFile()
        self.cycle = self

gc.collect()
gc.disable()
cycle = Cycle()
unrelated_fd = cycle.stream.fileno()
del cycle
actual_iterdir = Path.iterdir
actual_open = os.open
calls = 0
opened = []
def tracked_open(*args, **kwargs):
    fd = actual_open(*args, **kwargs)
    opened.append(fd)
    return fd

def collect_at_second_snapshot(path):
    global calls
    if str(path) == '/proc/self/fd':
        calls += 1
        if calls == 2:
            gc.collect()
    return actual_iterdir(path)

case = PortfolioBindingTests('test_regular_reader_rejects_links_directories_and_cleans_descriptors')
result = unittest.TestResult()
try:
    with patch.object(Path, 'iterdir', collect_at_second_snapshot), patch.object(portfolio.os, 'open', tracked_open):
        case.run(result)
finally:
    gc.enable()
closed = []
for fd in set(opened):
    try:
        os.fstat(fd)
    except OSError:
        closed.append(fd)
print(json.dumps({'authoredOnly': True, 'testsRun': result.testsRun, 'failures': [s.splitlines()[-1] for _,s in result.failures], 'errors': [s for _,s in result.errors], 'fdSnapshots': calls, 'allCapturedReaderDescriptorsClosed': set(closed)==set(opened), 'capturedUniqueDescriptorCount': len(set(opened)), 'qualification': 'Demonstrates an unrelated cyclic file collection can make exact existing global-count assertion fail with no captured reader descriptor left open. Does not establish that this was actual CI cause.'}))
