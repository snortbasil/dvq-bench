"""DVQ-Bench command line.

    dvq compose         # benchmark composition, no API keys needed
    dvq rubric          # rubric summary
    dvq run --models anthropic/claude-... openai/gpt-...   # the leaderboard (needs keys)
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from .loaders import load_rules, load_tasks

app = typer.Typer(add_completion=False, help="Data-Visualization Quality benchmark.")
console = Console()


@app.command()
def compose() -> None:
    """Report the benchmark composition (runs with no API keys)."""
    tasks = load_tasks()
    rules = load_rules()
    families: dict[str, int] = {}
    domains: dict[str, int] = {}
    failure_modes = 0
    referenced: set[str] = set()
    for t in tasks:
        families[t.family] = families.get(t.family, 0) + 1
        domains[t.domain] = domains.get(t.domain, 0) + 1
        failure_modes += len(t.failure_modes)
        referenced.update(r.split("-")[0] for r in t.applicable_rules)

    console.print(f"\n[bold]DVQ-Bench[/bold] — {len(tasks)} tasks across {len(families)} chart families\n")
    fam = Table("family", "tasks")
    for k in sorted(families):
        fam.add_row(k, str(families[k]))
    console.print(fam)

    console.print(f"\nDomains: {', '.join(f'{d} ({n})' for d, n in sorted(domains.items()))}")
    console.print(f"Failure modes enumerated: {failure_modes} (mean {failure_modes / max(1, len(tasks)):.1f}/task)")
    sources = {r.source for r in rules}
    console.print(f"Canon coverage: tasks reference {len(referenced & sources)}/{len(sources)} rule sources")
    det = sum(1 for r in rules if r.check.type == "deterministic")
    vis = sum(1 for r in rules if r.check.type == "vision")
    man = sum(1 for r in rules if r.check.type == "manual")
    console.print(f"Rubric: {len(rules)} cards ({det} deterministic, {vis} vision, {man} manual)\n")


@app.command()
def rubric() -> None:
    """Summarize the rubric by source and check type."""
    rules = load_rules()
    by_source: dict[str, int] = {}
    for r in rules:
        by_source[r.source] = by_source.get(r.source, 0) + 1
    t = Table("source", "cards")
    for k in sorted(by_source):
        t.add_row(k, str(by_source[k]))
    console.print(t)
    console.print(f"[bold]{len(rules)}[/bold] cards total\n")


if __name__ == "__main__":
    app()
