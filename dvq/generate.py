"""Generation step: ask a model to design a chart for a task.

The model is the independent variable of the benchmark. It receives the task
intent, the data description, and the canon principles that apply, and must
return a structured ChartSpec (title, mark, encodings, axis floor, source, ...)
plus a D3 function body for the renderer. Structured output is validated with
pydantic and retried once, provider-agnostically."""

from __future__ import annotations

import json
import re

from .loaders import rules_for_task
from .providers import Completion, complete
from .schemas import ChartSpec, Task

_SYSTEM = """You are a data-visualization designer. Given a request and the data available, \
design the single best chart: honest, legible, and appropriate to the analytical intent. \
Apply the design principles provided. Return ONLY a JSON object with these fields:
{
  "title": "a takeaway title that states the finding, not just the variable",
  "mark": "line|area|bar|scatter|point",
  "encodings": [{"channel":"x|y|color|size","field":"...","scale":"linear|time|ordinal|log"}],
  "entities": ["the series or categories shown"],
  "value_label": "what the measured quantity is",
  "unit": "e.g. %, USD, per capita",
  "source": {"name":"...","url":"..."},
  "annotations": ["only the moments that carry the story"],
  "palette": ["#hex", ...],
  "value_axis_min": 0,
  "sorted": true,
  "d3_code": "function body: (svg, data, d3, {width,height}) => { ... }; append one <svg>"
}
Never invent data values. Choose value_axis_min honestly (0 for bars/areas)."""


def _extract_json(s: str) -> dict:
    t = s.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", t, re.I)
    if fence:
        t = fence.group(1).strip()
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b != -1:
        t = t[a : b + 1]
    return json.loads(t)


def _prompt(task: Task) -> str:
    rules = rules_for_task(task)[:12]
    principles = "\n".join(f"- {r.principle}" for r in rules)
    return (
        f"Request: {task.intent}\n\n"
        f"Data available: {task.data.description} (shape: {task.data.shape}).\n\n"
        f"Design principles that apply:\n{principles}\n\n"
        f"Design the chart and return the JSON."
    )


async def generate_spec(model: str, task: Task, temperature: float = 0.0) -> tuple[ChartSpec, Completion]:
    user = _prompt(task)
    last_err = ""
    comp = None
    for attempt in range(2):
        comp = await complete(model, _SYSTEM, user, max_tokens=2000, temperature=temperature)
        try:
            return ChartSpec.model_validate(_extract_json(comp.text)), comp
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            user = _prompt(task) + f"\n\nYour previous reply did not parse ({last_err}). Return only valid JSON."
    raise ValueError(f"model {model} did not return a valid ChartSpec: {last_err}")
