"""The deterministic scorer separates a well-designed chart from a poor one, and
enforces the corrected line-baseline rule (Correll et al. 2020). Runs with no
API keys."""

from dvq.schemas import ChartSpec, Encoding, Source
from dvq.score.deterministic import score_deterministic


def _good() -> ChartSpec:
    return ChartSpec(
        title="Extreme poverty has fallen by more than half since 1990",
        mark="bar",
        encodings=[Encoding(channel="y", field="value", scale="linear"),
                   Encoding(channel="x", field="country", scale="ordinal")],
        entities=["A", "B", "C"],
        value_label="Share in extreme poverty",
        unit="%",
        source=Source(name="Our World in Data", url="https://ourworldindata.org/poverty"),
        annotations=["2020 reversal"],
        value_axis_min=0,
        sorted=True,
    )


def _bad() -> ChartSpec:
    return ChartSpec(
        title="poverty",  # names the variable, not a takeaway
        mark="bar",
        encodings=[Encoding(channel="y", field="value", scale="linear")],
        entities=["A", "B", "C", "D", "E"],
        value_label="",
        unit="",
        source=Source(),  # no source
        annotations=[],
        value_axis_min=40,  # truncated baseline on a bar chart
        sorted=False,  # unsorted ranking
    )


def test_good_beats_bad():
    good = score_deterministic(_good(), [])
    bad = score_deterministic(_bad(), [])
    assert good.score > bad.score
    assert good.publication_ready is True
    assert bad.publication_ready is False


def test_truncated_bar_fails_high():
    bad = score_deterministic(_bad(), [])
    baseline = next(f for f in bad.findings if f.rule_id == "tufte-zero-baseline")
    assert baseline.status == "fail" and baseline.severity == "high"


def test_missing_source_fails():
    bad = score_deterministic(_bad(), [])
    src = next(f for f in bad.findings if f.rule_id == "integrity-source-cited")
    assert src.status == "fail"


if __name__ == "__main__":
    test_good_beats_bad()
    test_truncated_bar_fails_high()
    test_missing_source_fails()
    g, b = score_deterministic(_good(), []), score_deterministic(_bad(), [])
    print(f"good={g.score}/100 pub-ready={g.publication_ready}  bad={b.score}/100 pub-ready={b.publication_ready}")
    print("all scorer tests passed")
