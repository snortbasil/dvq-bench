"""Load the rubric and task suite from the bundled JSON, and select the rules
that apply to a given task or chart shape (trigger-indexed, not embeddings:
at ~130 curated cards an explicit index beats a vector store and stays
inspectable)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .schemas import Rule, RuleSet, Task, TaskSet

_HERE = Path(__file__).parent
RUBRIC_DIR = _HERE / "rubric"
TASKS_DIR = _HERE / "tasks"


@lru_cache(maxsize=1)
def load_rules() -> list[Rule]:
    rules: list[Rule] = []
    for path in sorted(RUBRIC_DIR.glob("*.json")):
        rs = RuleSet.model_validate_json(path.read_text())
        for r in rs.rules:
            r.source = r.source or rs.source
            rules.append(r)
    return rules


@lru_cache(maxsize=1)
def load_tasks() -> list[Task]:
    tasks: list[Task] = []
    for path in sorted(TASKS_DIR.glob("*.json")):
        ts = TaskSet.model_validate_json(path.read_text())
        for t in ts.tasks:
            t.family = t.family or ts.family
            tasks.append(t)
    return tasks


def rules_for_task(task: Task) -> list[Rule]:
    """The rules a task declares applicable, matched by source prefix."""
    prefixes = set(task.applicable_rules)
    if not prefixes:
        return load_rules()
    out = []
    for r in load_rules():
        if r.source in prefixes or any(r.id.startswith(p) for p in prefixes):
            out.append(r)
    return out


def load_rules_json() -> list[dict]:
    """Raw rule dicts, for stuffing into a generation prompt."""
    return [json.loads(p.read_text()) for p in sorted(RUBRIC_DIR.glob("*.json"))]
