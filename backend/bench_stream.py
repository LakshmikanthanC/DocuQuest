import json
import time

import httpx

BASE = "http://localhost:8000/api"

token = httpx.post(
    f"{BASE}/auth/login",
    json={"email": "admin@example.com", "password": "admin12345"},
    timeout=30.0,
).json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}


def timed_stream(question: str) -> tuple[float, float, str, bool]:
    t0 = time.perf_counter()
    ttft = None
    text = []
    final = None
    has_context = False
    n_tokens = 0

    with httpx.stream(
        "POST",
        f"{BASE}/chat/stream",
        json={"question": question},
        headers=headers,
        timeout=300.0,
    ) as r:
        r.raise_for_status()
        event = None
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
                if event == "token":
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    text.append(data["text"])
                    n_tokens += 1
                elif event == "done":
                    final = data["answer"]
                    has_context = data["has_context"]

    total = time.perf_counter() - t0
    return ttft or total, total, final or "", has_context, n_tokens


for i, q in enumerate(
    [
        "What is a deadlock?",
        "Define page fault in two sentences.",
        "What is paging?",
    ],
    start=1,
):
    ttft, total, answer, has_ctx, n = timed_stream(q)
    print(
        f"run {i}: time-to-first-token={ttft * 1000:7.0f}ms  "
        f"total={total * 1000:7.0f}ms  events={n:>3}  "
        f"ansChars={len(answer):>4}  has_context={has_ctx}"
    )
    print(f"        {answer[:110]!r}")
