import json
import time

import httpx

from app.rag.chain import build_prompt
from app.rag.embeddings import embed_query
from app.rag.vector_store import similarity_search

USER = "24a106a17eca48a791c50ea7af21005d"

vec = embed_query("Define page fault in two sentences.")
chunks = similarity_search(user_id=USER, embedding=vec, top_k=4)
print(f"chunks retrieved: {len(chunks)}")
print(f"context chars    : {sum(len(c.content) for c in chunks)}")

prompt = build_prompt("Define page fault in two sentences.", chunks)
print(f"prompt chars     : {len(prompt)}")


def run(label, num_predict, num_ctx=4096, top_k=4):
    body = {
        "model": "llama3.1",
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.1,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "top_k": top_k,
        },
    }
    t0 = time.perf_counter()
    r = httpx.post("http://localhost:11434/api/generate", json=body, timeout=300.0)
    wall = (time.perf_counter() - t0) * 1000
    d = r.json()
    print(
        f"{label:<28} wall={wall:7.0f}ms  prompt_tok={d['prompt_eval_count']:>5} "
        f"prefill={d['prompt_eval_duration']/1e6:6.0f}ms  out_tok={d['eval_count']:>4} "
        f"gen={d['eval_duration']/1e6:6.0f}ms  "
        f"tok/s={d['eval_count']/max(d['eval_duration']/1e9,1e-9):5.1f}  load={d['load_duration']/1e6:.0f}ms"
    )
    return d


run("warmup", 16)
run("prefill only (num_predict=1)", 1)
run("typical answer", 128)
run("typical answer #2", 128)
run("ctx=2048", 128, num_ctx=2048)
run("ctx=1024", 128, num_ctx=1024)
