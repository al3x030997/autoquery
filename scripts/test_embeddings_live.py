#!/usr/bin/env python3
"""
Live smoke test for embedding pipeline against real Ollama.

Requires:
    docker compose exec ollama ollama pull bge-large-en-v1.5
    # or: ollama pull bge-large-en-v1.5
"""

import asyncio
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from autoquery.embeddings.model import OllamaEmbeddingModel


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def main():
    model = OllamaEmbeddingModel()
    print(f"Model: {model.model_name}")
    print(f"URL:   {model.ollama_url}")
    print(f"Dims:  {model.dimensions}")
    print()

    agent_text = (
        "Represent this literary agent profile for retrieval: "
        "This agent is looking for: "
        "I am actively seeking literary fiction, upmarket women's fiction, "
        "and narrative nonfiction. I love character-driven stories with "
        "beautiful prose and emotional depth."
    )
    ms_text = (
        "Represent this manuscript to find matching literary agents: "
        "Genre: Literary Fiction\n"
        "Audience: Adult\n"
        "A novel about a woman returning to her hometown after twenty years, "
        "confronting the secrets her family buried."
    )
    unrelated_text = (
        "Represent this manuscript to find matching literary agents: "
        "Genre: Hard Science Fiction\n"
        "A technical manual about spacecraft propulsion systems "
        "and orbital mechanics for interplanetary travel."
    )

    print("Embedding agent profile...")
    agent_vec = await model.embed(agent_text)
    print(f"  dims={len(agent_vec)}, L2 norm={math.sqrt(sum(x*x for x in agent_vec)):.6f}")

    print("Embedding matching manuscript...")
    ms_vec = await model.embed(ms_text)
    print(f"  dims={len(ms_vec)}, L2 norm={math.sqrt(sum(x*x for x in ms_vec)):.6f}")

    print("Embedding unrelated manuscript...")
    unrelated_vec = await model.embed(unrelated_text)
    print(f"  dims={len(unrelated_vec)}, L2 norm={math.sqrt(sum(x*x for x in unrelated_vec)):.6f}")

    sim_match = cosine_similarity(agent_vec, ms_vec)
    sim_unrelated = cosine_similarity(agent_vec, unrelated_vec)

    print()
    print(f"Agent <-> matching manuscript:   {sim_match:.4f}")
    print(f"Agent <-> unrelated manuscript:  {sim_unrelated:.4f}")
    print()

    if sim_match > sim_unrelated:
        print("PASS: Matching manuscript is closer to agent than unrelated one.")
    else:
        print("WARN: Unrelated manuscript scored higher — model may need tuning.")


if __name__ == "__main__":
    asyncio.run(main())
