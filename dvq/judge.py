"""Tier two: the vision judge. Binary per-criterion verdicts on the rendered
pixels, each with a required evidence sentence, temperature 0 — never a single
holistic score (Zheng et al. 2023; Shankar et al. 2024). Calibration against
expert labels (per-criterion TPR/TNR, Cohen's kappa) is the open work; until
measured, verdicts are directional."""

from __future__ import annotations

import json
import re

from .providers import complete
from .schemas import ChartSpec, Finding

_CRITERIA = [
    ("vision-annotation-overlap", "ware", "No overlapping labels", "high",
     "No text label or annotation overlaps another label or a data mark so as to impair reading either."),
    ("vision-focal-point", "gestalt", "Clear focal point", "medium",
     "The eye lands first on the element carrying the title's takeaway, not on chrome or an incidental bright element."),
    ("vision-text-legibility", "typography", "Text legible at size", "medium",
     "All text is readable at 100% zoom: nothing clipped, truncated, or smaller than ~10px."),
    ("vision-color-distinguish", "color", "Series distinguishable", "medium",
     "Every series is distinguishable from its neighbors, including under red-green color-vision deficiency."),
]

_SYSTEM = ("You are the vision critique agent for data visualizations. Judge the figure against each "
           "criterion independently and literally, using only what is visible. Return ONLY a JSON array, "
           'one object per criterion: {"id","verdict":"pass"|"fail","evidence":"one sentence naming the '
           'element that decides it"}. Evidence is required even for pass.')


def _extract_array(s: str) -> list[dict]:
    t = s.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", t, re.I)
    if fence:
        t = fence.group(1).strip()
    a, b = t.find("["), t.rfind("]")
    if a != -1 and b != -1:
        t = t[a : b + 1]
    return json.loads(t)


async def judge_figure(model: str, png_b64: str, spec: ChartSpec) -> list[Finding]:
    criteria_text = "\n".join(f'- id "{cid}": {defn}' for cid, _, _, _, defn in _CRITERIA)
    user = f"Title (the claim): {spec.title}\nMark: {spec.mark}; series: {', '.join(spec.entities)}\n\nCriteria:\n{criteria_text}"
    comp = await complete(model, _SYSTEM, user, image_b64=png_b64, max_tokens=700, temperature=0.0)
    by_id = {v.get("id"): v for v in _extract_array(comp.text)}

    findings: list[Finding] = []
    for cid, source, label, severity, _ in _CRITERIA:
        v = by_id.get(cid)
        verdict = (v or {}).get("verdict")
        if verdict not in ("pass", "fail"):
            findings.append(Finding(rule_id=cid, source=source, label=label, severity=severity,
                                    status="warn", message="No verdict returned; unverified.", check_type="vision"))
        else:
            findings.append(Finding(rule_id=cid, source=source, label=label, severity=severity,
                                    status=verdict, message=(v.get("evidence") or "").strip() or "-",
                                    check_type="vision"))
    return findings
