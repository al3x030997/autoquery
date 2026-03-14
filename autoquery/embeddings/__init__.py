from .model import EmbeddingModel, OllamaEmbeddingModel
from .pipeline import (
    combine_manuscript_embeddings,
    embed_agent,
    embed_manuscript_fulltext,
    embed_manuscript_query_expanded,
    expand_query,
    recompute_all_agent_embeddings,
)

__all__ = [
    "EmbeddingModel",
    "OllamaEmbeddingModel",
    "combine_manuscript_embeddings",
    "embed_agent",
    "embed_manuscript_fulltext",
    "embed_manuscript_query_expanded",
    "expand_query",
    "recompute_all_agent_embeddings",
]
