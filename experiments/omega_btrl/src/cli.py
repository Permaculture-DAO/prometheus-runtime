"""Safe read-only CLI: untrusted file inputs can NEVER provide trust roots.

Usage: python -m src.cli candidate.json
Without an independently configured trusted host, result is always HOLD/NO_GO.
"""
from pathlib import Path
import json
import sys
from .trust_boundary import evaluate, safe_json, closed_result


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        print(json.dumps(closed_result(reasons=['EXPECTED_ONE_LOCAL_JSON_PATH'])))
        return 2
    try:
        path=Path(args[0])
        # CLI deliberately prevents loading a supplied trust store/cert via the request.
        if path.stat().st_size > 65536:
            raise ValueError('PAYLOAD_TOO_LARGE')
        candidate=safe_json(path.read_bytes())
        result=evaluate(candidate)
    except Exception:
        result=closed_result(reasons=['INPUT_OR_TRUST_ERROR_SAFE_HOLD'])
    print(json.dumps(result,sort_keys=True))
    return 0 if result['decision']=='ELIGIBLE_FOR_REVIEW' else 2

if __name__=='__main__':
    raise SystemExit(main())
