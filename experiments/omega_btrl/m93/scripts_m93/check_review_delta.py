#!/usr/bin/env python3
"""Fail closed except 37 M9.3 additions and one exact M6 workflow compatibility modification."""
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
# One pre-existing *workflow* may be modified, solely to extend the explicit
# M6 CI allowlist to this signed M9.3 workflow. No native code changes.
compat_workflow='.github/workflows/omega-btrl-shadow.yml'
compat_changes=0
added=0
for status,path in items:
    if status == 'M' and path == compat_workflow:
        compat_changes+=1
    elif status == 'A' and (path.startswith('experiments/omega_btrl/m93/') or path=='.github/workflows/omega-m93-review-only.yml'):
        added+=1
    else:
        raise SystemExit('OUT_OF_SCOPE_OR_NOT_BOUNDED:'+status+':'+path)
if compat_changes != 1 or added != 37 or len(items) != 38:
    raise SystemExit(f'UNEXPECTED_BOUNDED_DELTA:existing_workflow={compat_changes}:added={added}:total={len(items)}')
print('M93_BOUNDED_CI_COMPAT_DIFF_PASS',added,compat_changes)
