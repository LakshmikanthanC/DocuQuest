"""Extract charts and mermaid diagrams from a model answer.

Small local models follow a "append a fenced ```chart JSON block" instruction
unreliably. Measured against the models shipped with this project:

- ``llama3.1`` (1.2B, the configured default) ignores the instruction and writes
  a GitHub-flavoured markdown table instead.
- ``llama3.2:3b`` emits the correct JSON but drops the fence.
- ``qwen2.5:0.5b`` emits the fenced block correctly.

So the parser accepts a fenced block, a bare JSON object carrying a chart
``type``, and a mermaid fence. Whatever it extracts is removed from the prose, so
the answer never shows raw JSON to the reader. The frontend also charts markdown
tables, which is what the 1.2B default produces.

Extraction is deliberately forgiving: an unparseable or absurd block is left in
place rather than raising, because a bad chart must never lose the answer.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any, Literal

from pydantic import BaseModel, Field

ChartKind = Literal["bar", "hbar", "line", "pie"]

CHART_TYPES = ("bar", "hbar", "line", "pie")
# A mermaid diagram is a header keyword followed by real diagram syntax (arrows,
# nodes, braces). Requiring that stops the phrase "graph of the results" from
# being mistaken for a diagram.
MERMAID_START = re.compile(
    r"^(?:graph|flowchart)\s+(?:TD|TB|BT|RL|LR|td|tb|bt|rl|lr)"
    r"|^sequenceDiagram|^classDiagram|^stateDiagram",
    re.IGNORECASE,
)

# Guards against a runaway generation being parsed as one enormous object.
MAX_BODY_CHARS = 8_000
MAX_POINTS = 60
MAX_LABEL_CHARS = 80
MAX_TITLE_CHARS = 120

_TYPE_ALIASES = {
    "column": "bar",
    "vertical_bar": "bar",
    "bars": "hbar",
    "horizontal_bar": "hbar",
    "area": "line",
    "trend": "line",
    "doughnut": "pie",
}


class ChartPoint(BaseModel):
    label: str = Field(max_length=MAX_LABEL_CHARS)
    value: float


class Chart(BaseModel):
    type: ChartKind
    title: str = Field(default="", max_length=MAX_TITLE_CHARS)
    data: list[ChartPoint] = Field(min_length=1, max_length=MAX_POINTS)

    @property
    def total(self) -> float:
        return sum(point.value for point in self.data)

    @property
    def peak(self) -> float:
        return max((point.value for point in self.data), default=0.0)


# A fenced block tagged chart/json/mermaid, or an untagged fence whose body
# parses as a chart. The untagged case is what llama3.2:3b produces.
_FENCED = re.compile(
    r"```[ \t]*(?P<tag>chart|json|mermaid|graph)?[ \t]*\r?\n(?P<body>.*?)```",
    re.DOTALL | re.IGNORECASE,
)

def _iter_bare_objects(text: str) -> Iterator[tuple[int, int, str]]:
    """Yield ``(start, end, body)`` for every balanced ``{...}`` run in ``text``.

    A regex cannot match nested braces, and a chart's ``data`` array is full of
    them, so the braces are counted instead.
    """
    depth = 0
    start = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth:
                depth -= 1
                if depth == 0:
                    yield start, index + 1, text[start : index + 1]


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def normalise_chart(raw: Any) -> Chart | None:
    """Coerce a decoded object into a Chart, or return None if it is not one."""
    if not isinstance(raw, dict):
        return None

    kind = str(raw.get("type", "")).strip().lower()
    kind = _TYPE_ALIASES.get(kind, kind)
    if kind not in CHART_TYPES:
        return None

    data = raw.get("data")
    if not isinstance(data, list) or not data:
        return None

    points: list[ChartPoint] = []
    for item in data[:MAX_POINTS]:
        if not isinstance(item, dict):
            continue
        label = item.get("label", item.get("name", item.get("x")))
        value = item.get("value", item.get("y"))
        if label is None or value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not _finite(numeric):
            continue
        points.append(
            ChartPoint(label=str(label)[:MAX_LABEL_CHARS], value=numeric)
        )

    if not points:
        return None

    try:
        return Chart(
            type=kind,
            title=str(raw.get("title", ""))[:MAX_TITLE_CHARS],
            data=points,
        )
    except Exception:
        return None


def normalise_mermaid(body: str) -> str | None:
    """Return the body if it looks like mermaid, else None."""
    text = body.strip()
    if not text or len(text) > MAX_BODY_CHARS:
        return None
    if not MERMAID_START.match(text):
        return None
    # A keyword alone is not a diagram; mermaid needs edges or nodes to draw.
    if not re.search(r"(?:-->|---|==>|->>|->|\[\(|\[|\{|\()", text):
        return None
    return text


def _chart_from_text(body: str) -> Chart | None:
    text = body.strip()
    if not text or len(text) > MAX_BODY_CHARS:
        return None
    try:
        return normalise_chart(json.loads(text))
    except json.JSONDecodeError:
        return None


def extract(text: str) -> tuple[str, Chart | None, str | None]:
    """Split an answer into ``(prose, chart, mermaid)``.

    Extracted blocks are removed from the prose. A block that fails to parse is
    left in place, because silently deleting a line of an answer is worse than
    showing a stray fence.
    """
    if not text or ("```" not in text and "{" not in text):
        return text.strip(), None, None

    chart: Chart | None = None
    mermaid: str | None = None

    def replace(match: re.Match[str]) -> str:
        nonlocal chart, mermaid
        body = match.group("body")
        tag = (match.group("tag") or "").lower()

        if tag in ("mermaid", "graph"):
            found = normalise_mermaid(body)
            if found:
                mermaid = mermaid or found
                return ""
            return match.group(0)

        if tag in ("chart", "json"):
            found = _chart_from_text(body)
            if found:
                chart = chart or found
                return ""
            return match.group(0)

        # Untagged fence: it is a chart, mermaid, or neither.
        found = _chart_from_text(body)
        if found:
            chart = chart or found
            return ""
        diagram = normalise_mermaid(body)
        if diagram:
            mermaid = mermaid or diagram
            return ""
        return match.group(0)

    prose = _FENCED.sub(replace, text)

    # Bare JSON with no fence at all, which is llama3.2:3b's other habit.
    if chart is None and mermaid is None and "```" not in text:
        for start, end, body in _iter_bare_objects(prose):
            found = _chart_from_text(body)
            if found:
                chart = found
                prose = prose[:start] + prose[end:]
                break

    prose = re.sub(r"\n{3,}", "\n\n", prose).strip()
    return prose, chart, mermaid
