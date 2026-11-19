#!/usr/bin/env python3
"""Fail closed when a review PR changes files outside the M9.3 add-only scope."""
from __future__ import annotations
import subprocess,sys

if len(sys.argv)!=3:
    raise SystemExit('usage: check_review_delta.py <base-sha> <head-sha>')
base,head=sys.argv[1:]
if any(len(x)!=40 or any(c not in '0123456789abcdef' for c in x.lower()) for x in (base,head)):
    raise SystemExit('INVALID_GIT_REF')
cp=subprocess.run(['git','diff','--name-status','--no-renames',base,head],text=True,capture_output=True,check=True)
items=[line.split('\t',1) for line in cp.stdout.splitlines() if line]
if not items:raise SystemExit('EMPTY_DIFF')
for status,path in items:
    if status != 'A' or not (path.startswith('experiments/omega_btrl/m93/') or path=='.github/workflows/omega-m93-review-only.yml'):
        raise SystemExit('OUT_OF_SCOPE_OR_NOT_ADD_ONLY:'+status+':'+path)
print('M93_ADD_ONLY_GITHUB_DIFF_PASS',len(items))
