import time

import httpx
from langchain_ollama import ChatOllama

OLLAMA = "http://localhost:11434"
PROMPT = (
    "Context:\n[1] source: Operating Systems.pdf (page 48)\n"
    + ("A deadlock is a situation in which a process waits for a resource held by "
       "another waiting process. " * 90)
    + "\n\nQuestion: What is a deadlock?\n\nAnswer:"
)


def raw(ctx: int, num_predict: int = 80) -> tuple[float, float, int, float]:
    body = {
        "model": "llama3.1",
        "prompt": PROMPT,
        "stream": True,
        "keep_alive": "30m",
        "options": {"temperature": 0.1, "num_ctx": ctx, "num_predict": num_predict},
    }
    t0 = time.perf_counter()
    first = None
    n = 0
    load = 0.0
    with httpx.stream("POST", f"{OLLAMA}/api/generate", json=body, timeout=300.0) as r:
        for line in r.iter_lines():
            if not line.startswith("data:"):
                continue
            d = json.loads(line[5:]) if False else __import__("json").loads(line[5:])
            if d.get("done"):
                load = d.get("load_duration", 0) / 1e6
                break
            if d.get("response"):
                if first is None:
                    first = time.perf_counter() - t0
                n += 1
    return (first or 0) * 1000, (time.perf_counter() - t0) * 1000, n, load


print("=== num_ctx=1024 (matches model native ctx), 3 consecutive calls ===")
for i in range(1, 4):
    ttft, total, n, load = raw(1024)
    print(f"  call {i}: TTFT={ttft:7.0f}ms total={total:7.0f}ms tokens={n:3d} load={load:6.0f}ms")

print("=== num_ctx=4096 (exceeds native ctx), 3 consecutive calls ===")
for i in range(1, 4):
    ttft, total, n, load = raw(4096)
    print(f"  call {i}: TTFT={ttft:7.0f}ms total={total:7.0f}ms tokens={n:3d} load={load:6.0f}ms")

print("=== back to 1024 (switch again) ===")
ttft, total, n, load = raw(1024)
print(f"  call 1: TTFT={ttft:7.0f}ms total={total:7.0f}ms tokens={n:3d} load={load:6.0f}ms")

print("=== langchain stream TTFT with num_ctx=1024, 3 calls ===")
for ctx in (1024,):
    llm = ChatOllama(
        model="llama3.1",
        base_url=OLLAMA,
        temperature=0.1,
        num_ctx=ctx,
        num_predict=80,
        keep_alive="30m",
    )
    for i in range(1, 4):
        t0 = time.perf_counter()
        first = None
        n = 0
        for c in llm.stream(PROMPT):
            if c.content:
                if first is None:
                    first = time.perf_counter() - t0
                n += 1
        print(
            f"  ctx={ctx} call {i}: TTFT={(first or 0)*1000:7.0f}ms "
            f"total={(time.perf_counter()-t0)*1000:7.0f}ms events={n}"
        )
