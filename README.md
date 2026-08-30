# DVQ-Bench

A benchmark for the **design quality** of AI-generated data visualizations.

Most chart benchmarks test whether a model can *read* a chart (chart QA) or
whether generated code *runs* (execution correctness). DVQ-Bench tests whether
the produced figure is *well designed*: honestly scaled, correctly encoded for
how people read magnitude, legible, restrained, and sourced. It scores a
figure against a canon-grounded rubric distilled from ~60 years of
graphical-perception research (Cleveland & McGill, Bertin, Ware, Tufte, Cairo).

## How it works

- **Tasks** (`dvq/tasks/`): realistic requests over public data, one per chart
  family (comparison, trend, distribution, part-to-whole, relationship,
  ranking, flow, geospatial, uncertainty). Each names the design-correct answer
  and the failure modes a weak response commits.
- **Rubric** (`dvq/rubric/`): criterion cards, each with a trigger, a check
  (deterministic / vision / manual), a severity, and a fix. The same rubric
  steers generation in the Exhibit product and scores output here.
- **Two-tier scoring.** Tier one is deterministic (baseline honesty, units,
  sources, series legibility, sorting) and runs with no model. Tier two is a
  vision-language-model judge with binary per-criterion verdicts, reserved for
  what only pixels reveal (label overlap, focal point, contrast). Cheap checks
  gate expensive ones.
- **Multi-provider.** Models are the independent variable. The provider layer
  runs the same task across Anthropic, OpenAI, Google, DeepSeek, Meta (via
  Together/Fireworks), and more, reporting quality, cost, and latency.

## Metrics

- **Publication-ready** (strict): no high-severity failure.
- **Capability score** (0-100): severity-weighted partial credit.
- **Vision agreement** (once calibrated): the judge's per-criterion agreement
  with expert labels (TPR, TNR, Cohen's kappa).

## Usage

```bash
uv sync
uv run dvq compose          # benchmark composition — no API keys
uv run dvq rubric           # rubric summary
uv run dvq run -m anthropic/claude-sonnet-4-5 -m openai/gpt-5.5   # leaderboard (needs keys)
```

The provider layer uses [litellm](https://github.com/BerriAI/litellm) by default
and can swap in [Vals AI's model-library](https://github.com/vals-ai/model-library)
(`uv sync --extra vals`). Rendering (tier two) executes D3 in headless Chromium
via Playwright — the one JavaScript step in an otherwise Python harness, because
D3 is the rendering substrate the field respects.

## Status

Deterministic tier, task suite, rubric, and multi-provider harness are built.
The vision judge and the human-calibration set are the current work; the
leaderboard needs provider API keys in `.env`. See `CONTRIBUTING.md` for the
roadmap.
