"""Pydantic schemas for DVQ-Bench.

Three groups: the rubric (canon criterion cards), the tasks (the benchmark
suite), and the run artifacts (what a model produces and how it scores). The
rubric and task JSON are the same files the Exhibit product uses, so the
benchmark and the tool it evaluates share one source of truth.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# --- Rubric ---------------------------------------------------------------

CheckType = Literal["deterministic", "vision", "manual"]
Severity = Literal["high", "medium", "low"]


class RuleCheck(BaseModel):
    type: CheckType
    detail: str


class Rule(BaseModel):
    id: str
    principle: str
    applies_when: str
    check: RuleCheck
    severity: Severity
    fix: str
    source: str = ""  # filled from the ruleset file on load
    evidence: Optional[str] = None  # e.g. "Correll et al. 2020"
    source_page: Optional[int] = None


class RuleSet(BaseModel):
    source: str
    rules: list[Rule]


# --- Tasks ----------------------------------------------------------------


class TaskData(BaseModel):
    provider: str
    description: str
    shape: str
    identifier: Optional[str] = None
    fetchable: bool = False


class TaskExpected(BaseModel):
    chart_family: str
    key_insight: str


class Task(BaseModel):
    id: str
    intent: str
    domain: str
    data: TaskData
    expected: TaskExpected
    failure_modes: list[str] = Field(default_factory=list)
    applicable_rules: list[str] = Field(default_factory=list)
    family: str = ""  # filled from the taskset file on load


class TaskSet(BaseModel):
    family: str
    tasks: list[Task]


# --- What a model produces ------------------------------------------------

MarkType = Literal["line", "area", "bar", "scatter", "point"]


class Encoding(BaseModel):
    channel: str  # x, y, color, size, ...
    field: str
    scale: str = ""  # linear, time, ordinal, log, ...


class Source(BaseModel):
    name: str = ""
    url: str = ""


class ChartSpec(BaseModel):
    """The structured chart a model is asked to design for a task. Structured so
    the deterministic tier can score it without pixels; ``d3_code`` is what the
    renderer executes for the vision tier."""

    title: str = ""
    mark: MarkType = "line"
    encodings: list[Encoding] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    value_label: str = ""
    unit: str = ""
    source: Source = Field(default_factory=Source)
    annotations: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    value_axis_min: Optional[float] = None  # declared floor of the value axis
    sorted: Optional[bool] = None  # for rankings: are marks sorted by value
    d3_code: str = ""  # function body: (svg, data, d3, {width,height}) => void


class DataRow(BaseModel):
    entity: str
    year: int
    value: float


# --- Scoring artifacts ----------------------------------------------------

Status = Literal["pass", "warn", "fail"]


class Finding(BaseModel):
    rule_id: str
    source: str
    label: str
    status: Status
    message: str
    check_type: CheckType
    severity: Severity


class Critique(BaseModel):
    score: int  # 0-100, severity-weighted capability score
    publication_ready: bool  # strict: no high-severity failure
    findings: list[Finding]
    note: str = ""


class RunResult(BaseModel):
    task_id: str
    family: str
    model: str
    seed: int
    spec: Optional[ChartSpec] = None
    critique: Optional[Critique] = None
    error: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
