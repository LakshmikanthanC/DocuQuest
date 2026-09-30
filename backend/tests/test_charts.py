"""Chart and diagram extraction from model answers.

Covers the three output shapes the local models actually produce: a fenced
```chart block (qwen2.5), an untagged fence or bare JSON (llama3.2:3b), and a
markdown table with no JSON at all (llama3.1, the configured default).
"""

from __future__ import annotations

import pytest

from app.rag import charts

FENCE = "```"


def fenced(tag: str, body: str) -> str:
    return f"{FENCE}{tag}\n{body}\n{FENCE}"


BAR = (
    '{"type":"bar","title":"Revenue","data":'
    '[{"label":"Q1","value":10},{"label":"Q2","value":14}]}'
)


# ---------------------------------------------------------------------------
# Shapes the models actually emit
# ---------------------------------------------------------------------------
def test_tagged_chart_block_is_extracted_and_removed():
    prose, chart, diagram = charts.extract(f"Revenue rose.\n\n{fenced('chart', BAR)}")

    assert chart is not None
    assert chart.type == "bar"
    assert chart.title == "Revenue"
    assert [point.label for point in chart.data] == ["Q1", "Q2"]
    assert prose == "Revenue rose.", "the JSON must never reach the reader"
    assert diagram is None


def test_untagged_fence_is_recognised():
    """llama3.2:3b emits the right JSON but drops the fence tag."""
    _, chart, _ = charts.extract(f"Here.\n\n{fenced('', BAR)}")
    assert chart is not None
    assert chart.type == "bar"


def test_bare_json_without_any_fence_is_recognised():
    _, chart, _ = charts.extract(f"Here.\n\n{BAR}")
    assert chart is not None
    assert chart.type == "bar"


def test_json_fence_is_recognised():
    _, chart, _ = charts.extract(f"Here.\n\n{fenced('json', BAR)}")
    assert chart is not None


def test_plain_prose_is_untouched():
    prose, chart, diagram = charts.extract("Machine learning learns from data.")
    assert (prose, chart, diagram) == ("Machine learning learns from data.", None, None)


def test_llama31_style_markdown_table_is_left_alone_for_the_frontend():
    """The 1.2B default writes a table; the backend must not mangle it."""
    table = "| Quarter | Revenue |\n| --- | --- |\n| Q1 | 10 |"
    prose, chart, _ = charts.extract(f"Revenue by quarter:\n\n{table}")
    assert chart is None
    assert table in prose


# ---------------------------------------------------------------------------
# Mermaid
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "body",
    [
        "flowchart TD\n  A[Start] --> B[End]",
        "graph LR\n  A --> B",
        "sequenceDiagram\n  Alice->>Bob: hi",
    ],
)
def test_mermaid_diagrams_are_extracted(body: str):
    prose, chart, diagram = charts.extract(
        f"Flow:\n\n{fenced('mermaid', body)}"
    )

    assert diagram == body.strip()
    assert chart is None
    assert prose == "Flow:"


def test_untagged_fence_containing_mermaid_is_recognised():
    _, _, diagram = charts.extract(fenced("", "flowchart TD\n A --> B"))
    assert diagram is not None


def test_untagged_paragraph_is_not_treated_as_mermaid():
    _, _, diagram = charts.extract(fenced("", "graph of the results"))
    assert diagram is None


# ---------------------------------------------------------------------------
# Tolerating what the models get wrong
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw_type", "expected"),
    [
        ("bar", "bar"),
        ("column", "bar"),
        ("vertical_bar", "bar"),
        ("hbar", "hbar"),
        ("horizontal_bar", "hbar"),
        ("line", "line"),
        ("area", "line"),
        ("pie", "pie"),
        ("doughnut", "pie"),
        ("BAR", "bar"),
    ],
)
def test_chart_type_aliases_and_casing(raw_type: str, expected: str):
    _, chart, _ = charts.extract(
        fenced("chart", f'{{"type":"{raw_type}","data":[{{"label":"a","value":1}}]}}')
    )
    assert chart is not None and chart.type == expected


def test_alternative_data_keys_are_accepted():
    """Small models reach for name/y, x/y, or label/value interchangeably."""
    _, chart, _ = charts.extract(
        fenced("chart", '{"type":"bar","data":[{"name":"a","y":2}]}')
    )
    assert chart is not None
    assert (chart.data[0].label, chart.data[0].value) == ("a", 2.0)

    _, chart, _ = charts.extract(
        fenced("chart", '{"type":"bar","data":[{"x":"b","value":3}]}')
    )
    assert chart is not None
    assert chart.data[0].label == "b"


def test_numeric_strings_are_coerced():
    _, chart, _ = charts.extract(
        fenced("chart", '{"type":"bar","data":[{"label":"Q1","value":"12.5"}]}')
    )
    assert chart is not None
    assert chart.data[0].value == 12.5


@pytest.mark.parametrize(
    "body",
    [
        "{not json at all}",
        '{"type":"bar"}',
        '{"type":"bar","data":[]}',
        '{"type":"unknown","data":[{"label":"a","value":1}]}',
        '{"type":"bar","data":[{"label":"a"}]}',
        '{"type":"bar","data":[{"label":"a","value":"abc"}]}',
        '{"type":"bar","data":"nope"}',
        "[]",
        '{"type":"bar","data":[{"label":"a","value":null}]}',
    ],
)
def test_unusable_blocks_are_dropped_and_the_prose_survives(body: str):
    prose, chart, _ = charts.extract(f"Answer text.\n\n{fenced('chart', body)}")

    assert chart is None
    assert "Answer text." in prose


def test_non_finite_values_are_rejected():
    """A NaN or Infinity would poison the SVG maths downstream."""
    _, chart, _ = charts.extract(
        fenced(
            "chart",
            '{"type":"bar","data":[{"label":"a","value":NaN},'
            '{"label":"b","value":2}]}',
        )
    )
    assert chart is not None
    assert [point.label for point in chart.data] == ["b"]


def test_a_block_that_fails_to_parse_is_left_in_the_prose():
    """Deleting a line of an answer is worse than showing a stray fence."""
    raw = f"Answer text.\n\n{fenced('chart', '{oops')}"
    prose, chart, _ = charts.extract(raw)

    assert chart is None
    assert "Answer text." in prose
    assert "oops" in prose, "the unparseable block should not be silently dropped"


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------
def test_point_count_is_capped():
    points = ",".join(
        f'{{"label":"p{i}","value":{i}}}' for i in range(charts.MAX_POINTS + 40)
    )
    _, chart, _ = charts.extract(fenced("chart", f'{{"type":"bar","data":[{points}]}}'))

    assert chart is not None
    assert len(chart.data) == charts.MAX_POINTS


def test_oversized_labels_are_truncated():
    _, chart, _ = charts.extract(
        fenced(
            "chart",
            '{"type":"bar","data":[{"label":"%s","value":1}]}'
            % ("x" * 400),
        )
    )
    assert chart is not None
    assert len(chart.data[0].label) <= charts.MAX_LABEL_CHARS


def test_absurdly_long_block_is_ignored_rather_than_parsed():
    body = '{"type":"bar","data":[' + "x" * 20_000
    _, chart, _ = charts.extract(f"Answer.\n\n{fenced('chart', body)}")
    assert chart is None


def test_extracting_twice_is_stable():
    once = charts.extract(f"Prose.\n\n{fenced('chart', BAR)}")
    twice = charts.extract(once[0])
    assert twice == (once[0], None, None)


def test_totals_and_peak_are_computed_for_rendering():
    _, chart, _ = charts.extract(fenced("chart", BAR))
    assert chart is not None
    assert chart.total == 24.0
    assert chart.peak == 14.0


def test_empty_input_is_safe():
    assert charts.extract("") == ("", None, None)
