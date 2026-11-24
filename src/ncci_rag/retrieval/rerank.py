"""Cross-encoder reranking.

Bi-encoder embeddings compare a question and a passage as two separate vectors. A
cross-encoder reads them *together* and scores how well the passage answers the
question, which is much more precise but too slow to run over the whole index. So we
run it only on the ~30 candidates fused from keyword, vector, and code search.

It also gives us something RRF cannot: a calibrated-ish absolute relevance score
(0-1 after a sigmoid). RRF scores depend only on ranks, so "rank 1" looks the same
whether the best passage is perfect or irrelevant. The reranker score is what the
"not in the manual" gate uses.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np


@lru_cache(maxsize=2)
def _load(model_name: str):
    from sentence_transformers import CrossEncoder  # optional dependency

    return CrossEncoder(model_name, max_length=512)


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        logits = np.asarray(_load(self.model_name).predict([(query, p) for p in passages]), dtype=np.float32)
        if logits.min() < 0 or logits.max() > 1:  # model returns raw logits
            logits = 1.0 / (1.0 + np.exp(-logits))
        return [float(x) for x in logits]
