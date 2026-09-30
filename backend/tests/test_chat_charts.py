"""Charts and mermaid diagrams end to end through the API contract.

The streaming and buffered chat routes must both carry the chart, and the
frontend's markdown-table fallback depends on a table-only answer reaching the
client intact.
"""

from __future__ import annotations

import json

import fitz
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import ANSWER

CHART_JSON = json.dumps(
    {
        "type": "bar",
        "title": "Revenue",
        "data": [
            {"label": "Q1", "value": 10},
            {"label": "Q2", "value": 14},
        ],
    }
)

CORPUS = ["Machine learning learns patterns from data."]
QUESTION = "What is machine learning?"


def upload(client: TestClient, auth: dict, name: str, pages: list[str]) -> dict:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 100), text, fontsize=11)
    data = doc.tobytes()
    doc.close()

    response = client.post(
        "/api/documents",
        headers=auth,
        files={"file": (name, data, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def patch_llm(monkeypatch, answer: str):
    """Patch the model so it replies with `answer`, for both invoke and stream."""

    class LLM:
        prompts: list[str] = []

        def invoke(self, prompt: str):
            self.prompts.append(prompt)
            return type("R", (), {"content": answer})()

        def stream(self, prompt: str):
            self.prompts.append(prompt)
            # Trailing fenced blocks arrive in one last chunk, as a real model
            # emits them only after the prose is done.
            head, _, tail = answer.partition("\n\n```")
            for word in head.split(" "):
                yield type("R", (), {"content": word + " "})()
            if tail:
                yield type("R", (), {"content": f"\n\n```{tail}"})()

    llm = LLM()
    monkeypatch.setattr("app.rag.chain.get_llm", lambda: llm)
    return llm


# ---------------------------------------------------------------------------
# Buffered route
# ---------------------------------------------------------------------------
def test_buffered_chat_returns_the_chart_and_hides_the_json(
    client: TestClient, auth: dict, monkeypatch
):
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(monkeypatch, f"Revenue rose.\n\n```chart\n{CHART_JSON}\n```")

    body = client.post("/api/chat", headers=auth, json={"question": QUESTION}).json()

    assert body["chart"] is not None
    assert body["chart"]["type"] == "bar"
    assert body["chart"]["title"] == "Revenue"
    assert body["chart"]["data"] == [
        {"label": "Q1", "value": 10.0},
        {"label": "Q2", "value": 14.0},
    ]
    assert "```" not in body["answer"], "the raw block must not reach the reader"
    assert "Revenue rose." in body["answer"]


def test_ordinary_answer_carries_no_chart(client: TestClient, auth: dict):
    upload(client, auth, "report.pdf", CORPUS)

    body = client.post("/api/chat", headers=auth, json={"question": QUESTION}).json()

    assert body["chart"] is None
    assert body["diagram"] is None
    assert body["answer"] == ANSWER


def test_mermaid_diagram_reaches_the_client(client: TestClient, auth: dict, monkeypatch):
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(
        monkeypatch,
        "Flow:\n\n```mermaid\nflowchart TD\n  A[Start] --> B[End]\n```",
    )

    body = client.post("/api/chat", headers=auth, json={"question": QUESTION}).json()

    assert body["diagram"] is not None
    assert "flowchart TD" in body["diagram"]
    assert body["chart"] is None
    assert "```" not in body["answer"]


def test_chart_is_recorded_in_history(client: TestClient, auth: dict, monkeypatch):
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(monkeypatch, f"Here.\n\n```chart\n{CHART_JSON}\n```")

    client.post("/api/chat", headers=auth, json={"question": QUESTION})
    history = client.get("/api/chat/history", headers=auth).json()

    answer = history["messages"][1]
    assert answer["chart"]["type"] == "bar"
    assert "```" not in answer["content"]


def test_unparseable_block_leaves_the_answer_intact(
    client: TestClient, auth: dict, monkeypatch
):
    """A broken chart must never cost the reader the answer."""
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(monkeypatch, "Revenue rose.\n\n```chart\n{oops\n```")

    body = client.post("/api/chat", headers=auth, json={"question": QUESTION}).json()

    assert body["chart"] is None
    assert "Revenue rose." in body["answer"]


def test_unknown_chart_type_is_dropped_not_rejected(
    client: TestClient, auth: dict, monkeypatch
):
    """A model asking for a type we do not render must not 500."""
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(
        monkeypatch,
        'Here.\n\n```chart\n{"type":"radar","data":'
        '[{"label":"a","value":1},{"label":"b","value":2}]}\n```',
    )

    response = client.post("/api/chat", headers=auth, json={"question": QUESTION})

    assert response.status_code == 200
    assert response.json()["chart"] is None


# ---------------------------------------------------------------------------
# Streaming route
# ---------------------------------------------------------------------------
def sse_payloads(response) -> list[dict]:
    """Every `data:` payload of an SSE response, in order."""
    payloads = []
    for line in response.iter_lines():
        if isinstance(line, str) and line.startswith("data: "):
            payloads.append(json.loads(line[len("data: ") :]))
    return payloads


def test_streamed_chat_sends_the_chart_in_the_done_event(
    client: TestClient, auth: dict, monkeypatch
):
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(monkeypatch, f"Revenue rose.\n\n```chart\n{CHART_JSON}\n```")

    with client.stream(
        "POST", "/api/chat/stream", headers=auth, json={"question": QUESTION}
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        payloads = sse_payloads(response)

    done = payloads[-1]
    assert done["answer"] == "Revenue rose."
    assert done["has_context"] is True
    assert done["chart"]["type"] == "bar"
    assert done["chart"]["data"][1]["label"] == "Q2"
    assert done["diagram"] is None
    assert "```" not in done["answer"]


def test_streamed_chat_agrees_with_the_buffered_route(
    client: TestClient, auth: dict, monkeypatch
):
    """The two routes must not disagree about the same answer."""
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(monkeypatch, f"Revenue rose.\n\n```chart\n{CHART_JSON}\n```")

    buffered = client.post("/api/chat", headers=auth, json={"question": QUESTION}).json()
    with client.stream(
        "POST", "/api/chat/stream", headers=auth, json={"question": QUESTION}
    ) as response:
        streamed = sse_payloads(response)[-1]

    assert streamed["answer"] == buffered["answer"]
    assert streamed["chart"] == buffered["chart"]


# ---------------------------------------------------------------------------
# Interactions with the rest of the pipeline
# ---------------------------------------------------------------------------
def test_prompt_asks_for_a_chart(client: TestClient, auth: dict, offline_models):
    upload(client, auth, "report.pdf", CORPUS)
    client.post("/api/chat", headers=auth, json={"question": QUESTION})

    prompt = offline_models.prompts[-1]
    assert "```chart" in prompt
    assert '"type":"bar"' in prompt


def test_markdown_table_answer_passes_through_for_the_frontend(
    client: TestClient, auth: dict, monkeypatch
):
    """llama3.1 writes a table instead of JSON; the frontend charts that."""
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(
        monkeypatch,
        "Revenue by quarter:\n\n| Quarter | Revenue |\n| --- | --- |\n"
        "| Q1 | 10 |\n| Q2 | 14 |",
    )

    body = client.post("/api/chat", headers=auth, json={"question": QUESTION}).json()

    assert body["chart"] is None, "the backend does not invent charts from tables"
    assert "| Quarter | Revenue |" in body["answer"]
    assert "| Q1 | 10 |" in body["answer"]


def test_no_context_answer_is_never_given_a_chart(
    client: TestClient, auth: dict, monkeypatch
):
    upload(client, auth, "report.pdf", CORPUS)
    patch_llm(monkeypatch, f"Revenue rose.\n\n```chart\n{CHART_JSON}\n```")
    monkeypatch.setattr(
        "app.api.routes_chat.vector_store.similarity_search", lambda **_: []
    )

    body = client.post("/api/chat", headers=auth, json={"question": QUESTION}).json()

    assert body["has_context"] is False
    assert body["chart"] is None
    assert body["sources"] == []


def test_relevance_floor_still_applies_before_charts(
    client: TestClient, auth: dict, offline_models
):
    """A chart is only ever built from chunks that cleared the floor."""
    upload(client, auth, "report.pdf", ["Coral reefs host diverse marine life."])

    before = len(offline_models.prompts)
    body = client.post(
        "/api/chat",
        headers=auth,
        json={"question": "What were the quarterly payroll and revenue figures?"},
    ).json()

    assert body["has_context"] is False
    assert body["chart"] is None
    assert len(offline_models.prompts) == before
    assert settings.min_relevance_score > 0
