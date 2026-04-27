"""Health check orchestrator — run all 10 dimensions and report.

The 10th dimension (`dim_ingest`) reports N/A on the Copilot backend, so
operators on Copilot still see effectively a 9-dimension report.
"""
import inspect
import sys
from ..health.scoring import overall_score
from ..health import (dim_freshness, dim_schema, dim_latency, dim_corpus,
                      dim_summary_coverage, dim_repo_coverage, dim_concurrency,
                      dim_e2e, dim_disclosure, dim_ingest)
from ..util.format_output import fmt_json

DIMS = [dim_freshness, dim_schema, dim_latency, dim_corpus,
        dim_summary_coverage, dim_repo_coverage, dim_concurrency, dim_e2e,
        dim_disclosure, dim_ingest]

_EMOJI_ZONES = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴",
                "CALIBRATING": "⚪", "N/A": "⚫"}
_ASCII_ZONES = {"GREEN": "[OK]", "AMBER": "[--]", "RED": "[!!]",
                "CALIBRATING": "[..]", "N/A": "[NA]"}


def _zone_icons() -> dict[str, str]:
    """Use emoji when stdout can encode them, fall back to ASCII otherwise.

    Windows console (cp1252) chokes on the 🟢/🟡/🔴 glyphs and crashes the
    whole report half-rendered. ASCII tags remain readable on every terminal.
    """
    enc = (getattr(sys.stdout, "encoding", "") or "").lower()
    if "utf" in enc:
        return _EMOJI_ZONES
    return _ASCII_ZONES


ZONE_ICON = _zone_icons()


def _call_check(dim, backend):
    """Call dim.check() with the backend if it accepts one, else without."""
    sig = inspect.signature(dim.check)
    if "backend" in sig.parameters:
        return dim.check(backend=backend)
    return dim.check()


def run(args, backend=None) -> int:
    results = [_call_check(d, backend) for d in DIMS]
    score = overall_score(results)
    hints = [r["hint"] for r in results if r["zone"] not in ("GREEN", "N/A") and r.get("hint")]

    if getattr(args, "json", False):
        print(fmt_json({"overall_score": score, "dims": results, "top_hints": hints[:3]}))
    else:
        print(f"\n{'Dim':<3s} {'Name':<22s} {'Zone':<8s} {'Score':>5s}  Detail")
        print("-" * 70)
        for i, r in enumerate(results, 1):
            icon = ZONE_ICON.get(r["zone"], "?")
            score_str = f"{r['score']:5.1f}" if r.get("score") is not None else "  -  "
            print(f" {i:<2d} {r['name']:<22s} {icon} {r['zone']:<5s} {score_str}  {r['detail']}")
        print("-" * 70)
        print(f"    {'Overall':<22s}        {score:5.1f}")
        if hints:
            print("\n💡 Hints:")
            for h in hints[:3]:
                print(f"   • {h}")
        print()
    return 0
