"""The leaderboard run: each model designs a chart for each task; score all,
aggregate, and report. Concurrency is bounded and rate-limit tolerant; the model
is the independent variable so the table compares providers on the same tasks.

Deterministic scoring runs on the spec alone (no data fetch needed for v0; the
line-truncation check degrades gracefully). The vision judge (--judge) renders
the D3 and scores pixels, and needs the render extra plus a VLM.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .generate import generate_spec
from .loaders import load_tasks
from .schemas import RunResult
from .score.deterministic import score_deterministic

console = Console()


async def _one(model: str, task, seed: int, sem: asyncio.Semaphore, do_judge: bool) -> RunResult:
    async with sem:
        try:
            spec, comp = await generate_spec(model, task, temperature=0.0 if seed == 0 else 0.7)
            critique = score_deterministic(spec, [])
            if do_judge:
                from .render.render import render_png
                from .judge import judge_figure
                png = await render_png(spec)
                if png:
                    vision = await judge_figure(model, png, spec)
                    findings = critique.findings + vision
                    critique.findings = findings
                    critique.publication_ready = not any(
                        f.severity == "high" and f.status == "fail" for f in findings
                    )
            return RunResult(
                task_id=task.id, family=task.family, model=model, seed=seed, spec=spec,
                critique=critique, tokens_in=comp.tokens_in, tokens_out=comp.tokens_out,
                cost_usd=comp.cost_usd, latency_ms=comp.latency_ms,
            )
        except Exception as e:  # noqa: BLE001
            return RunResult(task_id=task.id, family=task.family, model=model, seed=seed, error=str(e))


def run_benchmark(models, seeds=1, families=None, concurrency=6, out="results", judge=False) -> None:
    if not any(os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY", "TOGETHER_API_KEY")):
        console.print("[red]No provider API key found in the environment.[/red] Set at least one "
                      "(ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, ...) and retry.")
        raise SystemExit(1)

    tasks = [t for t in load_tasks() if not families or t.family in families]
    jobs = [(m, t, s) for m in models for t in tasks for s in range(seeds)]
    console.print(f"Running {len(jobs)} jobs: {len(models)} models × {len(tasks)} tasks × {seeds} seed(s), "
                  f"concurrency {concurrency}{' + vision judge' if judge else ''}.")

    async def _all() -> list[RunResult]:
        sem = asyncio.Semaphore(concurrency)
        return await asyncio.gather(*[_one(m, t, s, sem, judge) for (m, t, s) in jobs])

    results = asyncio.run(_all())

    outdir = Path(out)
    outdir.mkdir(exist_ok=True)
    with (outdir / "results.jsonl").open("w") as f:
        for r in results:
            f.write(r.model_dump_json() + "\n")

    # Aggregate per model.
    table = Table("model", "n", "errors", "pub-ready %", "mean score", "mean $", "mean ms")
    for m in models:
        rs = [r for r in results if r.model == m]
        ok = [r for r in rs if r.critique]
        errs = sum(1 for r in rs if r.error)
        pub = 100 * sum(1 for r in ok if r.critique.publication_ready) / len(ok) if ok else 0
        mean_score = sum(r.critique.score for r in ok) / len(ok) if ok else 0
        mean_cost = sum(r.cost_usd for r in rs) / len(rs) if rs else 0
        mean_ms = sum(r.latency_ms for r in rs) / len(rs) if rs else 0
        table.add_row(m, str(len(rs)), str(errs), f"{pub:.0f}", f"{mean_score:.1f}",
                      f"${mean_cost:.4f}", f"{mean_ms:.0f}")
    console.print(table)
    console.print(f"\nWrote {len(results)} results to {outdir / 'results.jsonl'}")
