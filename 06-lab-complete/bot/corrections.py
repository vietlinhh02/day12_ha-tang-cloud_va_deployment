from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)


@dataclass
class Correction:
    original_claim: str
    correct_info: str
    corrected_by: str  # Discord username
    timestamp: str
    message_id: str | None = None


@dataclass
class CorrectionStore:
    corrections: list[Correction] = field(default_factory=list)
    _vectorizer: TfidfVectorizer = field(default_factory=TfidfVectorizer)
    _matrix = None

    def add(self, correction: Correction) -> None:
        self.corrections.append(correction)
        self._rebuild_index()
        log.info(
            "Correction added by %s: '%s' -> '%s'",
            correction.corrected_by,
            correction.original_claim[:60],
            correction.correct_info[:60],
        )

    def get_relevant(self, query: str, top_k: int = 3) -> list[Correction]:
        """Find corrections relevant to a query using TF-IDF similarity."""
        if not self.corrections or self._matrix is None:
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()

        scored = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results: list[Correction] = []
        for idx, score in scored[:top_k]:
            if score < 0.1:
                break
            results.append(self.corrections[idx])
        return results

    def to_prompt_block(self, query: str, top_k: int = 5) -> str:
        """Format relevant corrections as a block for the LLM system prompt."""
        relevant = self.get_relevant(query, top_k)
        if not relevant:
            return ""
        lines = ["=== KNOWN CORRECTIONS (do NOT repeat these mistakes) ==="]
        for i, c in enumerate(relevant, 1):
            lines.append(
                f"[{i}] WRONG: {c.original_claim}\n"
                f"    CORRECT: {c.correct_info}\n"
                f"    (corrected by {c.corrected_by})"
            )
        return "\n".join(lines)

    def _rebuild_index(self) -> None:
        if not self.corrections:
            return
        texts = [
            f"{c.original_claim} {c.correct_info}" for c in self.corrections
        ]
        self._matrix = self._vectorizer.fit_transform(texts)

    # ── persistence ─────────────────────────────────────────────────────────

    def save_to_file(self, path: str | Path) -> None:
        data = [asdict(c) for c in self.corrections]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
        log.info("Saved %d corrections to %s", len(data), path)

    def load_from_file(self, path: str | Path) -> None:
        p = Path(path)
        if not p.exists():
            return
        data = json.loads(p.read_text())
        self.corrections = [Correction(**item) for item in data]
        self._rebuild_index()
        log.info("Loaded %d corrections from %s", len(self.corrections), path)
