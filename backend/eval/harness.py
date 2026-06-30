"""Evaluation harness for the SHL retrieval pipeline.

Runs every sample conversation through the retriever in two modes and
reports IR metrics so we can quantify the impact of each design change.

Modes
-----
- ``baseline`` — original weighted (min-max normalised) fusion of dense
  + sparse, no reranker, no soft filters. Reproduced exactly inside
  ``HybridRetriever`` for an apples-to-apples diff.
- ``rrf`` — the new pipeline: RRF fusion + soft metadata penalties +
  cross-encoder reranking (when the model is available).

Metrics
-------
- **Recall@k** — fraction of gold items returned in the top-k.
  Primary metric per the assignment.
- **MRR@10** — mean reciprocal rank of the first gold hit. Sensitive to
  precision at position 1.
- **nDCG@10** — discounted gain; rewards putting more gold hits near the
  top.

Run
---
::

    python -m eval.harness            # both modes, all conversations
    python -m eval.harness --mode rrf # single mode
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from app.catalog.loader import load_catalog
from app.config import get_settings
from app.retrieval.hybrid import HybridRetriever
from app.schemas import ConversationState

from .parse_conversations import EvalCase, load_eval_cases

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "sample_conversations"


@dataclass
class CaseResult:
    name: str
    gold: int
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    mrr_at_10: float
    ndcg_at_10: float
    confidence: float
    hits_in_top10: int


def _normalise(u: str) -> str:
    return u.strip().rstrip("/").lower()


def _hits(returned_urls: list[str], gold: set[str], k: int) -> int:
    return sum(1 for u in returned_urls[:k] if _normalise(u) in gold)


def _mrr(returned_urls: list[str], gold: set[str], k: int) -> float:
    for i, u in enumerate(returned_urls[:k], start=1):
        if _normalise(u) in gold:
            return 1.0 / i
    return 0.0


def _ndcg(returned_urls: list[str], gold: set[str], k: int) -> float:
    dcg = 0.0
    for i, u in enumerate(returned_urls[:k], start=1):
        if _normalise(u) in gold:
            dcg += 1.0 / math.log2(i + 1)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(gold), k) + 1))
    return dcg / ideal if ideal else 0.0


def evaluate_case(retriever: HybridRetriever, case: EvalCase, mode: str) -> CaseResult:
    state = ConversationState()
    items, diag = retriever.search(
        state, k=10, raw_query=case.query, mode=mode, return_diagnostics=True
    )
    urls = [a.url for a, _ in items]
    gold = {_normalise(u) for u in case.gold_urls}
    n_gold = len(gold)
    hits10 = _hits(urls, gold, 10)
    return CaseResult(
        name=case.name,
        gold=n_gold,
        recall_at_1=_hits(urls, gold, 1) / n_gold,
        recall_at_5=_hits(urls, gold, 5) / n_gold,
        recall_at_10=hits10 / n_gold,
        mrr_at_10=_mrr(urls, gold, 10),
        ndcg_at_10=_ndcg(urls, gold, 10),
        confidence=diag.confidence,
        hits_in_top10=hits10,
    )


def _aggregate(results: list[CaseResult]) -> dict[str, float]:
    n = len(results) or 1
    return {
        "recall@1": sum(r.recall_at_1 for r in results) / n,
        "recall@5": sum(r.recall_at_5 for r in results) / n,
        "recall@10": sum(r.recall_at_10 for r in results) / n,
        "mrr@10": sum(r.mrr_at_10 for r in results) / n,
        "ndcg@10": sum(r.ndcg_at_10 for r in results) / n,
        "mean_confidence": sum(r.confidence for r in results) / n,
        "cases": n,
    }


def run(modes: list[str], json_out: Path | None = None) -> dict:
    """Run one or more retrieval configurations against the eval corpus.

    Supported modes:
        baseline       — min-max weighted fusion, no reranker (the v1 system).
        rrf_no_rerank  — RRF fusion + soft metadata, reranker disabled.
        rrf            — full pipeline: RRF + soft metadata + cross-encoder.
    """
    settings = get_settings()
    catalog = load_catalog(settings.catalog_file)
    cases = load_eval_cases(SAMPLES)
    if not cases:
        raise SystemExit(f"No eval cases found in {SAMPLES}")
    if not catalog:
        raise SystemExit("Catalog is empty — cannot evaluate")

    report: dict = {"catalog_size": len(catalog), "n_cases": len(cases), "modes": {}}
    for mode in modes:
        enable_re = mode == "rrf"
        retriever = HybridRetriever(catalog, settings, enable_reranker=enable_re)
        # The retriever has two fusion modes ("weighted" and "rrf"); the
        # "rrf_no_rerank" ablation runs rrf-fusion without the CE pass.
        search_mode = "weighted" if mode == "baseline" else "rrf"
        per_case = [evaluate_case(retriever, c, search_mode) for c in cases]
        report["modes"][mode] = {
            "aggregate": _aggregate(per_case),
            "per_case": [c.__dict__ for c in per_case],
            "reranker_enabled": enable_re and bool(retriever.reranker and retriever.reranker.available),
        }

    if json_out:
        json_out.write_text(json.dumps(report, indent=2))
    return report


_METRIC_KEYS = ("recall@1", "recall@5", "recall@10", "mrr@10", "ndcg@10", "mean_confidence")


def _print_report(report: dict) -> None:
    print(f"\nCatalog: {report['catalog_size']} assessments  |  Eval cases: {report['n_cases']}\n")
    header = f"{'mode':<16}  {'R@1':>6}  {'R@5':>6}  {'R@10':>6}  {'MRR@10':>7}  {'nDCG@10':>8}  {'conf':>6}  rerank"
    print(header)
    print("-" * len(header))
    for mode, block in report["modes"].items():
        a = block["aggregate"]
        print(
            f"{mode:<16}  {a['recall@1']:.3f}  {a['recall@5']:.3f}  {a['recall@10']:.3f}  "
            f"{a['mrr@10']:.3f}   {a['ndcg@10']:.3f}    {a['mean_confidence']:.2f}    "
            f"{'on' if block['reranker_enabled'] else 'off'}"
        )
    if "baseline" in report["modes"] and "rrf" in report["modes"]:
        b = report["modes"]["baseline"]["aggregate"]
        r = report["modes"]["rrf"]["aggregate"]
        print("\nΔ (rrf − baseline):")
        for k in _METRIC_KEYS:
            d = r[k] - b[k]
            arrow = "▲" if d > 0 else ("▼" if d < 0 else "·")
            print(f"  {k:<16} {arrow} {d:+.3f}")


def _markdown_report(report: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Retrieval evaluation\n")
    lines.append(f"Catalog: **{report['catalog_size']}** assessments · "
                 f"Cases: **{report['n_cases']}**\n")
    lines.append("| mode | R@1 | R@5 | R@10 | MRR@10 | nDCG@10 | conf | rerank |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|:-:|")
    for mode, block in report["modes"].items():
        a = block["aggregate"]
        lines.append(
            f"| `{mode}` | {a['recall@1']:.3f} | {a['recall@5']:.3f} | "
            f"{a['recall@10']:.3f} | {a['mrr@10']:.3f} | {a['ndcg@10']:.3f} | "
            f"{a['mean_confidence']:.2f} | {'on' if block['reranker_enabled'] else 'off'} |"
        )
    if "baseline" in report["modes"] and "rrf" in report["modes"]:
        b = report["modes"]["baseline"]["aggregate"]
        r = report["modes"]["rrf"]["aggregate"]
        lines.append("\n## Δ (rrf − baseline)\n")
        lines.append("| metric | Δ |")
        lines.append("|---|---:|")
        for k in _METRIC_KEYS:
            lines.append(f"| {k} | {r[k] - b[k]:+.3f} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="SHL retrieval eval harness")
    parser.add_argument(
        "--mode",
        choices=["baseline", "rrf", "rrf_no_rerank", "both", "ablation"],
        default="both",
        help="`ablation` runs baseline + rrf_no_rerank + rrf to isolate the "
             "impact of fusion vs reranker.",
    )
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "report.json")
    parser.add_argument("--md", type=Path, default=ROOT / "eval" / "REPORT.md",
                        help="Markdown summary path.")
    args = parser.parse_args()
    if args.mode == "both":
        modes = ["baseline", "rrf"]
    elif args.mode == "ablation":
        modes = ["baseline", "rrf_no_rerank", "rrf"]
    else:
        modes = [args.mode]
    report = run(modes, json_out=args.out)
    _print_report(report)
    args.md.write_text(_markdown_report(report))
    print(f"\nFull report → {args.out}\nMarkdown summary → {args.md}")


if __name__ == "__main__":
    main()

