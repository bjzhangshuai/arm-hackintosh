"""Reject nominal Rust passes containing Vulkan errors or silent test skips."""
import argparse
from pathlib import Path
import re


def check(log, returncode, expected_passed, allowed_ignored=0):
    if returncode != 0:
        raise ValueError(f'test process failed: {returncode}')
    if expected_passed <= 0 or allowed_ignored < 0:
        raise ValueError('invalid expected test counts')
    if re.search(r'VUID-|Validation Error|SKIP:|test result: FAILED', log, re.I):
        raise ValueError('validation error or skipped/failed execution in log')
    summaries = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', log)
    if not summaries:
        raise ValueError('missing completed test summary')
    passed = sum(int(p) for p, _, _ in summaries)
    failed = sum(int(f) for _, f, _ in summaries)
    ignored = sum(int(i) for _, _, i in summaries)
    if failed or passed != expected_passed or ignored != allowed_ignored:
        raise ValueError(f'unexpected counts: passed={passed} failed={failed} ignored={ignored}')
    return {'passed': passed, 'ignored': ignored, 'validation_errors': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--returncode', type=int, required=True)
    parser.add_argument('--expected-passed', type=int, required=True)
    parser.add_argument('--allowed-ignored', type=int, default=0)
    args = parser.parse_args()
    print(check(args.log.read_text(errors='replace'), args.returncode,
                args.expected_passed, args.allowed_ignored))
