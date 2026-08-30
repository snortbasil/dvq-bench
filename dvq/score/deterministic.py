"""Tier one of scoring: deterministic canon checks over a ChartSpec + data.

Ported from the Exhibit product's lint (one rubric, three uses: it steers
generation there and scores output here). Only what a plan and data can prove;
the perceptual checks (overlap, focal point) are tier two, the vision judge.
The line-chart baseline rule reflects Correll, Bertini & Franconeri (2020):
truncation exaggerates line charts too, so there is no silent exemption.
"""

from __future__ import annotations

from ..schemas import ChartSpec, Critique, DataRow, Finding, Severity, Status

_SEV_WEIGHT: dict[Severity, int] = {"high": 3, "medium": 2, "low": 1}
_STATUS_SCORE: dict[Status, float] = {"pass": 1.0, "warn": 0.5, "fail": 0.0}


def _f(rule_id, source, label, severity, status, message) -> Finding:
    return Finding(
        rule_id=rule_id, source=source, label=label, severity=severity,
        status=status, message=message, check_type="deterministic",
    )


def score_deterministic(spec: ChartSpec, data: list[DataRow]) -> Critique:
    n_series = max(1, len(spec.entities))
    values = [d.value for d in data] or [0.0]
    data_min = min(values)
    findings: list[Finding] = []

    # tufte: honest baseline. Bar/area must sit on zero; line must not truncate
    # away from the data floor (Correll et al. 2020) — no silent exemption.
    if spec.mark in ("bar", "area"):
        ok = spec.value_axis_min == 0
        findings.append(_f(
            "tufte-zero-baseline", "tufte", "Honest baseline", "high",
            "pass" if ok else "fail",
            "Value axis starts at zero; magnitude is honest (lie factor ~1)." if ok
            else f"{spec.mark} chart with axis floor {spec.value_axis_min}, not zero — magnitude is exaggerated.",
        ))
    else:
        truncated = spec.value_axis_min is not None and spec.value_axis_min > data_min
        findings.append(_f(
            "tufte-zero-baseline", "tufte", "Honest baseline", "high",
            "warn" if truncated else "pass",
            "Truncated floor exaggerates the change; disclose it (Correll et al. 2020)." if truncated
            else "Axis floor does not truncate below the data.",
        ))

    # bertin: categories separated by color or by an ordinal position channel.
    has_color = any(e.channel == "color" for e in spec.encodings)
    cat_on_axis = spec.mark == "bar" or any(
        e.channel in ("x", "y") and e.scale == "ordinal" for e in spec.encodings
    )
    if n_series > 1 and not has_color and not cat_on_axis:
        findings.append(_f("bertin-color-for-categories", "bertin", "Color encodes category", "high",
                           "fail", f"{n_series} series but no color or positional separation."))
    elif n_series == 1 and has_color:
        findings.append(_f("bertin-color-for-categories", "bertin", "Color encodes category", "high",
                           "warn", "Color on a single series adds ink without meaning."))
    else:
        findings.append(_f("bertin-color-for-categories", "bertin", "Color encodes category", "high",
                           "pass", "Categories separated by color or position, as appropriate."))

    # cleveland: too many overlaid lines are hard to track.
    findings.append(_f("cleveland-series-legibility", "cleveland-mcgill", "Series legibility", "medium",
                       "warn" if (spec.mark == "line" and n_series > 7) else "pass",
                       f"{n_series} lines is hard to track; consider small multiples." if (spec.mark == "line" and n_series > 7)
                       else "Series count is within a readable range."))

    # ware: a ranking should be sorted so rank is preattentive.
    if spec.mark == "bar":
        srt = spec.sorted is not False
        findings.append(_f("ware-sorted-ranking", "ware", "Ranking is sorted", "medium",
                           "pass" if srt else "warn",
                           "Bars sorted by value; rank reads preattentively." if srt
                           else "Bars unsorted; the ranking is hidden."))
    else:
        findings.append(_f("ware-sorted-ranking", "ware", "Ranking is sorted", "medium",
                           "pass", "Not a ranking; ordering rule does not apply."))

    # cairo: the title should assert the finding, not name the variable.
    t = spec.title.strip()
    takeaway = len(t) >= 24 and " " in t and t.lower() != spec.value_label.lower()
    findings.append(_f("cairo-takeaway-title", "cairo", "Title states a finding", "medium",
                       "pass" if takeaway else "warn",
                       "Title asserts the takeaway." if takeaway
                       else "Title reads like a variable name; state the conclusion."))

    # integrity: source cited.
    findings.append(_f("integrity-source-cited", "cairo", "Source cited", "high",
                       "pass" if spec.source.url else "fail",
                       f"Source attributed ({spec.source.name})." if spec.source.url
                       else "No data source cited; the figure cannot be checked."))

    # tufte: annotation restraint.
    findings.append(_f("tufte-annotation-restraint", "tufte", "Annotation restraint", "low",
                       "warn" if len(spec.annotations) > 4 else "pass",
                       f"{len(spec.annotations)} callouts risk clutter." if len(spec.annotations) > 4
                       else "Annotations restrained to what carries the story."))

    # integrity: units declared.
    findings.append(_f("integrity-units-declared", "tufte", "Units declared", "medium",
                       "pass" if (spec.unit.strip() or spec.value_label) else "warn",
                       "Quantity and unit are labeled." if (spec.unit.strip() or spec.value_label)
                       else "No unit declared; readers cannot interpret magnitude."))

    num = sum(_SEV_WEIGHT[f.severity] * _STATUS_SCORE[f.status] for f in findings)
    den = sum(_SEV_WEIGHT[f.severity] for f in findings)
    score = round((num / den) * 100) if den else 0
    publication_ready = not any(f.severity == "high" and f.status == "fail" for f in findings)

    return Critique(
        score=score,
        publication_ready=publication_ready,
        findings=findings,
        note="Deterministic tier. The vision judge adds overlap, contrast, and focal-point checks on rendered pixels.",
    )
