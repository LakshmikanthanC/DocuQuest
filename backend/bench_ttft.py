import json
import time

import httpx

OLLAMA = "http://localhost:11434"
BASE = "http://localhost:8000/api"

# Build a realistic RAG prompt using the app's own code.
from app.rag.chain import build_prompt
from app.rag.embeddings import embed_query
from app.rag.vector_store import similarity_search

USER = "24a106a17eca48a791c50ea7af21005d"
vec = embed_query("What is a deadlock?")
chunks = similarity_search(user_id=USER, embedding=vec, top_k=4)
prompt = build_prompt("What is a deadlock?", chunks)
print(f"prompt tokens approx: {len(prompt)//4}")

# 1. Raw Ollama streaming: when does the first token arrive?
for label, opts in [
    ("num_ctx=4096", {"num_ctx": 4096}),
    ("num_ctx=1024", {"num_ctx": 1024}),
]:
    body = {
        "model": "llama3.1",
        "prompt": prompt,
        "stream": True,
        "keep_alive": "30m",
        "options": {"temperature": 0.1, "num_predict": 64, **opts},
    }
    t0 = time.perf_counter()
    first = None
    n = 0
    load_ms = 0.0
    empty_before_done = 0
    raw_lines = 0
    with httpx.stream("POST", f"{OLLAMA}/api/generate", json=body, timeout=300.0) as r:
        print(f"  status={r.status_code} opts={opts}")
        for line in r.iter_lines():
            raw_lines += 1
            if not line.startswith("data:"):
                continue
            d = json.loads(line[5:])
            if d.get("error"):
                print(f"  ollama error: {d['error'][:300]}")
            if d.get("done"):
                load_ms = d.get("load_duration", 0) / 1e6
                if n == 0:
                    print(f"  done with NO text. keys={list(d.keys())}")
                break
            if d.get("response"):
                if first is None:
                    first = time.perf_counter() - t0
                n += 1
            else:
                empty_before_done += 1
    total = time.perf_counter() - t0
    ft = f"{first*1000:7.0f}ms" if first else "  never"
    print(
        f"raw ollama {label:<14} TTFT={ft} total={total*1000:7.0f}ms "
        f"tokens={n} lines={raw_lines} empty={empty_before_done} load={load_ms:.0f}ms"
    )

# 2. LangChain ChatOllama stream (what the backend uses).
from app.rag.chain import get_llm

llm = get_llm()
t0 = time.perf_counter()
first = None
n = 0
for chunk in llm.stream(prompt):
    if chunk.content:
        if first is None:
            first = time.perf_counter() - t0
        n += 1
total = time.perf_counter() - t0
ft = f"{first*1000:7.0f}ms" if first else "  never"
print(f"langchain stream      TTFT={ft} total={total*1000:7.0f}ms events={n}")

# 3. Buffered invoke for comparison.
t0 = time.perf_counter()
llm.invoke(prompt)
print(f"langchain invoke      total={(time.perf_counter()-t0)*1000:7.0f}ms")
